# Benchmark Dashboard Roadmap

## Q3 2024

- Roll out the Textual dashboard (`automation/ui_app.py`) for production Raspberry Pi fleets.
- Expand JSON summaries from `rpi4/bench/pi_bench.py` with percentile breakdowns for long-running deployments.
- Wire automated ingestion into Grafana/Prometheus exporters to bridge terminal dashboards with central observability.

## Q4 2024

- Introduce alert thresholds in the dashboard, enabling notifications when latency or throughput diverges from rolling
  averages.
- Add support for GPU metrics on Pi 5 hardware revisions.

## 2025 and beyond

- Allow remote agents to push benchmark payloads over MQTT/WebSocket transports for aggregated analytics.
- Provide APIs for exporting runs into CSV/Parquet for archival research workloads.
