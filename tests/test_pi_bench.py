from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json
import tempfile
import unittest

from rpi4.bench import pi_bench


class PiBenchSummaryTest(unittest.TestCase):
    def test_update_json_summary_creates_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            output_dir = tmp_path / "artifacts"
            output_dir.mkdir()

            run = pi_bench.execute_benchmarks(
                cpu_iterations=10,
                memory_sample_mb=1,
                disk_sample_mb=1,
                work_dir=tmp_path,
                tag="test",
            )
            csv_path = output_dir / "pi_bench.csv"
            pi_bench.append_run_to_csv(csv_path, run)
            summary = pi_bench.update_json_summary(
                output_dir / "pi_bench_summary.json",
                run,
                history_limit=5,
                csv_path=csv_path,
            )

            self.assertIn("metrics", summary)
            self.assertIn("runs", summary)
            self.assertEqual(summary["runs"][0]["tag"], "test")

            cpu_metrics = [
                key for key in summary["metrics"].keys() if key.startswith("pi_") or key.startswith("cpu")
            ]
            self.assertTrue(cpu_metrics)

            json_summary = json.loads((output_dir / "pi_bench_summary.json").read_text())
            self.assertEqual(json_summary["version"], 1)

    def test_update_json_summary_trims_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            output_dir = tmp_path / "artifacts"
            output_dir.mkdir()
            csv_path = output_dir / "pi_bench.csv"
            summary_path = output_dir / "pi_bench_summary.json"

            first_run = pi_bench.BenchmarkRun(
                run_id="run-1",
                timestamp=datetime.now(UTC),
                tag="first",
                system={"machine": "test"},
                metrics=[
                    pi_bench.BenchmarkMetric(
                        name="pi_compute_ms",
                        value=1.0,
                        unit="ms",
                        category="cpu",
                        metadata={"iterations": 1},
                    )
                ],
            )
            pi_bench.append_run_to_csv(csv_path, first_run)
            pi_bench.update_json_summary(
                summary_path,
                first_run,
                history_limit=2,
                csv_path=csv_path,
            )

            second_run = pi_bench.BenchmarkRun(
                run_id="run-2",
                timestamp=datetime.now(UTC),
                tag="second",
                system={"machine": "test"},
                metrics=[
                    pi_bench.BenchmarkMetric(
                        name="pi_compute_ms",
                        value=2.0,
                        unit="ms",
                        category="cpu",
                        metadata={"iterations": 1},
                    )
                ],
            )
            pi_bench.append_run_to_csv(csv_path, second_run)
            pi_bench.update_json_summary(
                summary_path,
                second_run,
                history_limit=2,
                csv_path=csv_path,
            )

            third_run = pi_bench.BenchmarkRun(
                run_id="run-3",
                timestamp=datetime.now(UTC),
                tag="third",
                system={"machine": "test"},
                metrics=[
                    pi_bench.BenchmarkMetric(
                        name="pi_compute_ms",
                        value=3.0,
                        unit="ms",
                        category="cpu",
                        metadata={"iterations": 1},
                    )
                ],
            )
            pi_bench.append_run_to_csv(csv_path, third_run)
            summary = pi_bench.update_json_summary(
                summary_path,
                third_run,
                history_limit=2,
                csv_path=csv_path,
            )

            history = summary["metrics"]["pi_compute_ms"]["history"]
            self.assertLessEqual(len(history), 2)
            self.assertEqual([entry["run_id"] for entry in history], ["run-2", "run-3"])

            runs = summary["runs"]
            self.assertEqual(len(runs), 2)
            self.assertEqual([entry["run_id"] for entry in runs], ["run-3", "run-2"])


if __name__ == "__main__":
    unittest.main()
