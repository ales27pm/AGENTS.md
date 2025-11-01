"""Textual UI application that visualizes Raspberry Pi benchmark trends."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:  # pragma: no cover - import guard for environments without Textual installed
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Vertical
    from textual.reactive import reactive
    from textual.widgets import Footer, Header, ScrollView, Static
    from rich.panel import Panel
    from rich.table import Table
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise RuntimeError(
        "textual is required to use the benchmark dashboard. Install it via 'pip install textual'."
    ) from exc


@dataclass(slots=True)
class MetricHistory:
    metric: str
    unit: str
    category: str
    history: List[Dict[str, Any]]
    latest: Dict[str, Any]
    average: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    change_pct: Optional[float]

    @property
    def values(self) -> List[float]:
        return [point["value"] for point in self.history]


def _load_summary(summary_path: Path) -> Dict[str, Any]:
    with summary_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sparkline(values: Iterable[float], *, width: int = 32) -> str:
    characters = "▁▂▃▄▅▆▇█"
    values_list = list(values)
    if not values_list:
        return "·" * width
    v_min = min(values_list)
    v_max = max(values_list)
    if v_max - v_min < 1e-9:
        return characters[0] * min(len(values_list), width)
    scaled = [int((value - v_min) / (v_max - v_min) * (len(characters) - 1)) for value in values_list]
    return "".join(characters[index] for index in scaled[-width:])


def _format_change(change_pct: Optional[float]) -> str:
    if change_pct is None:
        return "—"
    return f"{change_pct:+.2f}%"


def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"


class BenchmarkSummaryLoader:
    """Load and cache benchmark summary JSON."""

    def __init__(self, summary_path: Path) -> None:
        self._summary_path = summary_path
        self._last_mtime: Optional[float] = None
        self._cache: Optional[Dict[str, Any]] = None

    def load(self, *, force: bool = False) -> Dict[str, Any]:
        if not self._summary_path.exists():
            raise FileNotFoundError(self._summary_path)

        mtime = self._summary_path.stat().st_mtime
        if not force and self._cache is not None and mtime == self._last_mtime:
            return self._cache

        data = _load_summary(self._summary_path)
        self._cache = data
        self._last_mtime = mtime
        return data


class MetricTrend(Static):
    """Widget that renders a single metric summary."""

    def __init__(self, metric: MetricHistory) -> None:
        super().__init__()
        self.metric_history = metric
        self.update(self._render_panel())

    def update_metric(self, metric: MetricHistory) -> None:
        self.metric_history = metric
        self.update(self._render_panel())

    def _render_panel(self) -> Panel:
        metric = self.metric_history
        table = Table.grid(expand=True)
        table.add_row(f"[b]{metric.metric}[/b] ({metric.unit})")
        latest_ts = metric.latest.get("timestamp") if metric.latest else "—"
        latest_value = metric.latest.get("value") if metric.latest else None
        latest_str = _format_number(float(latest_value)) if latest_value is not None else "—"
        if metric.latest:
            table.add_row(
                f"Latest: {latest_str} {metric.unit if metric.unit else ''} @ {latest_ts}"
            )
        else:
            table.add_row("Latest: —")
        table.add_row(f"Average: {_format_number(metric.average)}")
        if metric.min_value is not None and metric.max_value is not None:
            table.add_row(
                f"Range: {_format_number(metric.min_value)} – {_format_number(metric.max_value)}"
            )
        else:
            table.add_row("Range: —")
        table.add_row(f"Change: {_format_change(metric.change_pct)}")
        table.add_row(f"Trend: {_sparkline(metric.values)}")
        return Panel(table, title=metric.category.capitalize(), padding=(1, 2))


class RunSummary(Static):
    """Display metadata about the latest benchmark run."""

    def update_from_runs(self, runs: List[Dict[str, Any]]) -> None:
        if not runs:
            self.update(Panel("No benchmark runs available", title="Latest run", padding=(1, 2)))
            return

        latest = runs[0]
        table = Table.grid(expand=True)
        table.add_row(f"Timestamp: {latest.get('timestamp', '—')}")
        table.add_row(f"Tag: {latest.get('tag') or '—'}")
        system = latest.get('system') or {}
        table.add_row(f"Platform: {system.get('platform', '—')}")
        table.add_row(f"Python: {system.get('python', '—')}")
        table.add_row(f"CPU cores: {system.get('cpu_count', '—')}")
        self.update(Panel(table, title="Latest run", padding=(1, 2)))


class DashboardView(ScrollView):
    """Scrollable container for benchmark cards."""

    data = reactive(None)

    def compose(self) -> ComposeResult:
        yield RunSummary(id="run-summary")
        yield Vertical(id="dashboard")

    def update_from_summary(self, summary: Dict[str, Any]) -> None:
        self.data = summary
        summary_widget = self.query_one("#run-summary", RunSummary)
        summary_widget.update_from_runs(summary.get("runs", []))

        container = self.query_one("#dashboard", Vertical)
        for child in list(container.children):
            child.remove()

        metrics = summary.get("metrics", {})
        for metric_name, payload in sorted(metrics.items()):
            history = MetricHistory(
                metric=metric_name,
                unit=payload.get("unit", ""),
                category=payload.get("category", "misc"),
                history=payload.get("history", []),
                latest=payload.get("latest", {}),
                average=payload.get("average"),
                min_value=payload.get("min"),
                max_value=payload.get("max"),
                change_pct=payload.get("change_pct"),
            )
            container.mount(MetricTrend(history))


class BenchmarkDashboardApp(App):
    """Textual app that surfaces benchmark history with periodic refreshes."""

    CSS_PATH = "ui_app.tcss/dashboard.tcss"
    BINDINGS = [Binding("q", "quit", "Quit"), Binding("r", "refresh", "Refresh")]

    def __init__(
        self,
        *,
        summary_path: Path,
        refresh_interval: float = 30.0,
    ) -> None:
        super().__init__()
        self.summary_path = summary_path
        self.refresh_interval = refresh_interval
        self.loader = BenchmarkSummaryLoader(summary_path)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()
        self.dashboard: DashboardView = DashboardView()
        yield self.dashboard

    async def on_mount(self) -> None:
        await self.refresh_dashboard(force=True)
        self.set_interval(self.refresh_interval, self.refresh_dashboard)

    async def refresh_dashboard(self, force: bool = False) -> None:
        try:
            summary = self.loader.load(force=force)
        except FileNotFoundError:
            self.dashboard.update_from_summary({"metrics": {}})
            self.notify(
                "No benchmark summary found. Run rpi4/bench/pi_bench.py to generate data.",
                severity="error",
            )
            return
        except json.JSONDecodeError as exc:
            self.dashboard.update_from_summary({"metrics": {}})
            self.notify(f"Failed to parse summary: {exc}", severity="error")
            return

        self.dashboard.update_from_summary(summary)
        self.sub_title = f"Last refresh: {datetime.now().isoformat(timespec='seconds')}"

    async def action_refresh(self) -> None:
        await self.refresh_dashboard(force=True)


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the benchmark dashboard UI")
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("benchmarks/pi_bench_summary.json"),
        help="Path to pi_bench summary JSON",
    )
    parser.add_argument(
        "--refresh",
        type=float,
        default=30.0,
        help="Seconds between automatic refreshes",
    )
    return parser.parse_args(argv)


def run_app(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    app = BenchmarkDashboardApp(summary_path=args.summary, refresh_interval=args.refresh)
    app.run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    run_app()
