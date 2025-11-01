# Benchmark Dashboard Styling

The Textual dashboard (`automation/ui_app.py`) loads styles from this directory.

## Launching dashboard mode

1. Generate or update benchmark data:
   ```bash
   python -m rpi4.bench.pi_bench --output-dir benchmarks
   ```
2. Start the dashboard UI (refreshes every 30 seconds by default):
   ```bash
   python -m automation.ui_app --summary benchmarks/pi_bench_summary.json --refresh 30
   ```

The app reads `pi_bench_summary.json`, refreshing on the cadence configured with
`--refresh`. When new runs are appended the trend lines update automatically.

## Styling notes

`dashboard.tcss` defines padding, borders, and layout for the metric cards. Feel
free to extend with additional palettes or animations as new panels are added.
