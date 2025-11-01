"""Utilities for running Raspberry Pi benchmarks and emitting structured metrics.

This module powers the dashboard pipeline by collecting a trio of lightweight
benchmarks (CPU, memory allocation, and disk throughput), appending the results
as CSV rows, and generating a JSON summary that the Textual UI can consume.

Typical usage from the command line::

    python -m rpi4.bench.pi_bench --output-dir benchmarks

The command will create/update ``pi_bench.csv`` and ``pi_bench_summary.json``
under the chosen output directory. The JSON file contains rolling aggregates for
trend analysis, including the last ``--history`` measurements for each metric.

The benchmarks are intentionally conservative so they can execute inside CI or a
headless Raspberry Pi without requiring root access.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import argparse
import csv
import json
import math
import os
from pathlib import Path
import platform
import statistics
import tempfile
import time
import tracemalloc
import uuid
from typing import Any, Dict, List, Optional, Sequence

DECIMAL_PLACES = 6
DEFAULT_OUTPUT_DIR = Path("benchmarks")
DEFAULT_HISTORY = 50


@dataclass(slots=True)
class BenchmarkMetric:
    """Represents a single measurement captured during a benchmark run."""

    name: str
    value: float
    unit: str
    category: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkRun:
    """Group of metrics captured at roughly the same time."""

    run_id: str
    timestamp: datetime
    tag: Optional[str]
    system: Dict[str, Any]
    metrics: List[BenchmarkMetric]


class BenchmarkError(RuntimeError):
    """Raised when a benchmark cannot complete successfully."""


def _gather_system_metadata() -> Dict[str, Any]:
    """Collect host details for traceability."""

    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
    }


def _bbp_pi(iterations: int) -> float:
    """Approximate PI using the Bailey–Borwein–Plouffe series."""

    # The Decimal module adds a lot of overhead, so we stay in floats. The
    # algorithm converges quickly enough for modest iteration counts.
    pi = 0.0
    for k in range(iterations):
        sixteen_pow = 16.0 ** k
        pi += (
            (4.0 / (8 * k + 1) - 2.0 / (8 * k + 4) - 1.0 / (8 * k + 5) - 1.0 / (8 * k + 6))
            / sixteen_pow
        )
    return pi


def run_cpu_benchmark(iterations: int) -> List[BenchmarkMetric]:
    """Measure how long it takes to approximate PI using the BBP series."""

    start = time.perf_counter()
    pi_estimate = _bbp_pi(iterations)
    elapsed = time.perf_counter() - start

    delta = abs(math.pi - pi_estimate)
    metrics = [
        BenchmarkMetric(
            name="pi_compute_ms",
            value=elapsed * 1000.0,
            unit="ms",
            category="cpu",
            metadata={"iterations": iterations, "pi_error": delta},
        ),
        BenchmarkMetric(
            name="pi_estimate",
            value=pi_estimate,
            unit="value",
            category="cpu",
            metadata={"iterations": iterations, "pi_error": delta},
        ),
        BenchmarkMetric(
            name="pi_error",
            value=delta,
            unit="abs",
            category="cpu",
            metadata={"iterations": iterations},
        ),
    ]
    return metrics


def run_memory_benchmark(sample_size_mb: int) -> List[BenchmarkMetric]:
    """Allocate a list of floats and capture allocation latency and peak usage."""

    elements = max(int(sample_size_mb * 1024 * 1024 / 8), 1)
    tracemalloc.start()
    start = time.perf_counter()
    # The comprehension keeps timings realistic while avoiding massive memory use.
    data = [float(i % 256) for i in range(elements)]
    elapsed = time.perf_counter() - start
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    # Ensure the allocated memory is released promptly.
    del data

    metrics = [
        BenchmarkMetric(
            name="alloc_ms",
            value=elapsed * 1000.0,
            unit="ms",
            category="memory",
            metadata={"sample_size_mb": sample_size_mb, "elements": elements},
        ),
        BenchmarkMetric(
            name="peak_usage_mb",
            value=peak / (1024 * 1024),
            unit="MB",
            category="memory",
            metadata={"sample_size_mb": sample_size_mb, "elements": elements},
        ),
    ]
    return metrics


def run_disk_benchmark(work_dir: Path, file_size_mb: int) -> List[BenchmarkMetric]:
    """Measure sequential write/read throughput inside ``work_dir``."""

    work_dir.mkdir(parents=True, exist_ok=True)
    block = os.urandom(1024 * 1024)
    iterations = max(file_size_mb, 1)
    temp_file = work_dir / "pi_bench_io_test.bin"

    # Write test
    start = time.perf_counter()
    with temp_file.open("wb") as handle:
        for _ in range(iterations):
            handle.write(block)
        handle.flush()
        os.fsync(handle.fileno())
    write_elapsed = time.perf_counter() - start
    total_bytes = iterations * len(block)
    write_mbps = (total_bytes / (1024 * 1024)) / write_elapsed if write_elapsed else 0.0

    # Read test
    start = time.perf_counter()
    with temp_file.open("rb") as handle:
        while handle.read(1024 * 1024):
            pass
    read_elapsed = time.perf_counter() - start
    read_mbps = (total_bytes / (1024 * 1024)) / read_elapsed if read_elapsed else 0.0

    temp_file.unlink(missing_ok=True)

    metrics = [
        BenchmarkMetric(
            name="write_mb_s",
            value=write_mbps,
            unit="MB/s",
            category="storage",
            metadata={"file_size_mb": file_size_mb},
        ),
        BenchmarkMetric(
            name="read_mb_s",
            value=read_mbps,
            unit="MB/s",
            category="storage",
            metadata={"file_size_mb": file_size_mb},
        ),
        BenchmarkMetric(
            name="write_time_ms",
            value=write_elapsed * 1000.0,
            unit="ms",
            category="storage",
            metadata={"file_size_mb": file_size_mb},
        ),
        BenchmarkMetric(
            name="read_time_ms",
            value=read_elapsed * 1000.0,
            unit="ms",
            category="storage",
            metadata={"file_size_mb": file_size_mb},
        ),
    ]
    return metrics


def execute_benchmarks(
    *,
    cpu_iterations: int,
    memory_sample_mb: int,
    disk_sample_mb: int,
    work_dir: Path,
    tag: Optional[str] = None,
) -> BenchmarkRun:
    """Run the three benchmark groups and return a structured run payload."""

    if cpu_iterations <= 0:
        raise BenchmarkError("cpu_iterations must be > 0")
    if memory_sample_mb <= 0:
        raise BenchmarkError("memory_sample_mb must be > 0")
    if disk_sample_mb <= 0:
        raise BenchmarkError("disk_sample_mb must be > 0")

    run_id = uuid.uuid4().hex
    timestamp = datetime.now(UTC)
    system = _gather_system_metadata()

    metrics: List[BenchmarkMetric] = []
    metrics.extend(run_cpu_benchmark(cpu_iterations))
    metrics.extend(run_memory_benchmark(memory_sample_mb))
    metrics.extend(run_disk_benchmark(work_dir=work_dir, file_size_mb=disk_sample_mb))

    return BenchmarkRun(
        run_id=run_id,
        timestamp=timestamp,
        tag=tag,
        system=system,
        metrics=metrics,
    )


def _ensure_csv_header(path: Path, fieldnames: Sequence[str]) -> None:
    if not path.exists() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()


def append_run_to_csv(path: Path, run: BenchmarkRun) -> None:
    """Append the benchmark run to ``path`` ensuring headers exist."""

    fieldnames = (
        "run_id",
        "timestamp",
        "tag",
        "category",
        "metric",
        "value",
        "unit",
        "metadata",
        "run_metadata",
    )
    _ensure_csv_header(path, fieldnames)

    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        for metric in run.metrics:
            writer.writerow(
                {
                    "run_id": run.run_id,
                    "timestamp": run.timestamp.isoformat(timespec="seconds"),
                    "tag": run.tag or "",
                    "category": metric.category,
                    "metric": metric.name,
                    "value": f"{metric.value:.{DECIMAL_PLACES}f}",
                    "unit": metric.unit,
                    "metadata": json.dumps(metric.metadata, sort_keys=True),
                    "run_metadata": json.dumps(run.system, sort_keys=True),
                }
            )


def _safe_float(value: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise BenchmarkError(f"Unable to convert value '{value}' to float") from exc


def _load_csv_records(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    with path.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        records: List[Dict[str, Any]] = []
        for row in reader:
            metadata: Dict[str, Any]
            try:
                metadata = json.loads(row.get("metadata", "{}"))
            except json.JSONDecodeError:
                metadata = {}
            try:
                run_metadata = json.loads(row.get("run_metadata", "{}"))
            except json.JSONDecodeError:
                run_metadata = {}
            records.append(
                {
                    "run_id": row.get("run_id", ""),
                    "timestamp": row.get("timestamp", ""),
                    "tag": row.get("tag") or None,
                    "category": row.get("category", ""),
                    "metric": row.get("metric", ""),
                    "value": _safe_float(row.get("value", "0")),
                    "unit": row.get("unit", ""),
                    "metadata": metadata,
                    "run_metadata": run_metadata,
                }
            )
    return records


def _summarize_metric_history(
    metric: str,
    values: List[Dict[str, Any]],
    *,
    history_limit: int,
) -> Dict[str, Any]:
    ordered = sorted(values, key=lambda item: item["timestamp"])
    history = ordered[-history_limit:]
    numeric_values = [item["value"] for item in history]
    latest = history[-1] if history else None

    summary: Dict[str, Any] = {
        "metric": metric,
        "unit": latest["unit"] if latest else values[0]["unit"] if values else "",
        "category": latest["category"] if latest else values[0]["category"] if values else "",
        "history": [
            {
                "timestamp": item["timestamp"],
                "run_id": item["run_id"],
                "value": item["value"],
                "tag": item["tag"],
            }
            for item in history
        ],
    }

    if latest:
        summary["latest"] = {
            "timestamp": latest["timestamp"],
            "value": latest["value"],
            "run_id": latest["run_id"],
            "tag": latest["tag"],
            "metadata": latest["metadata"],
        }
    if numeric_values:
        summary["average"] = statistics.fmean(numeric_values)
        summary["min"] = min(numeric_values)
        summary["max"] = max(numeric_values)
        if len(numeric_values) >= 2:
            previous = numeric_values[-2]
            latest_value = numeric_values[-1]
            if previous:
                summary["change_pct"] = ((latest_value - previous) / previous) * 100.0
            else:
                summary["change_pct"] = None
        else:
            summary["change_pct"] = None
    else:
        summary["average"] = None
        summary["min"] = None
        summary["max"] = None
        summary["change_pct"] = None

    return summary


def generate_json_summary(
    csv_path: Path,
    json_path: Path,
    *,
    history_limit: int = DEFAULT_HISTORY,
) -> Dict[str, Any]:
    """Build a JSON summary from the CSV history and persist it."""

    records = _load_csv_records(csv_path)
    grouped_metrics: Dict[str, List[Dict[str, Any]]] = {}
    runs: Dict[str, Dict[str, Any]] = {}

    for record in records:
        run_id = record["run_id"]
        runs.setdefault(
            run_id,
            {
                "run_id": run_id,
                "timestamp": record["timestamp"],
                "tag": record["tag"],
                "system": record["run_metadata"],
                "metrics": [],
            },
        )
        runs[run_id]["metrics"].append(
            {
                "category": record["category"],
                "metric": record["metric"],
                "value": record["value"],
                "unit": record["unit"],
                "metadata": record["metadata"],
            }
        )
        grouped_metrics.setdefault(record["metric"], []).append(record)

    metrics_summary = {
        metric: _summarize_metric_history(metric, values, history_limit=history_limit)
        for metric, values in grouped_metrics.items()
    }

    summary = {
        "version": 1,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "csv_path": str(csv_path),
        "history_limit": history_limit,
        "metrics": metrics_summary,
        "runs": sorted(
            runs.values(),
            key=lambda item: item["timestamp"],
            reverse=True,
        ),
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
    return summary


def _default_output_paths(output_dir: Path) -> Dict[str, Path]:
    output_dir = output_dir.expanduser().resolve()
    csv_path = output_dir / "pi_bench.csv"
    json_path = output_dir / "pi_bench_summary.json"
    return {"csv": csv_path, "json": json_path}


def _parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Raspberry Pi benchmarks and emit structured metrics")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for CSV/JSON artifacts")
    parser.add_argument("--history", type=int, default=DEFAULT_HISTORY, help="Rolling history depth for JSON summary")
    parser.add_argument("--cpu-iterations", type=int, default=2500, help="Iterations for the PI benchmark")
    parser.add_argument("--memory-mb", type=int, default=32, help="Megabytes to allocate for the memory benchmark")
    parser.add_argument("--disk-mb", type=int, default=16, help="Megabytes to read/write when testing disk throughput")
    parser.add_argument("--tag", type=str, default=None, help="Optional tag for the run (e.g. location or hardware label)")
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="Directory used for temporary disk IO tests",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    args = _parse_args(argv)
    paths = _default_output_paths(args.output_dir)

    run = execute_benchmarks(
        cpu_iterations=args.cpu_iterations,
        memory_sample_mb=args.memory_mb,
        disk_sample_mb=args.disk_mb,
        work_dir=args.work_dir,
        tag=args.tag,
    )

    append_run_to_csv(paths["csv"], run)
    summary = generate_json_summary(paths["csv"], paths["json"], history_limit=args.history)

    return summary


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    result = main()
    print(json.dumps(result, indent=2))
