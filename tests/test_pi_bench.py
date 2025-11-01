from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from rpi4.bench import pi_bench


class PiBenchSummaryTest(unittest.TestCase):
    def test_generate_json_summary_creates_expected_keys(self) -> None:
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
            summary = pi_bench.generate_json_summary(
                csv_path, output_dir / "pi_bench_summary.json", history_limit=5
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


if __name__ == "__main__":
    unittest.main()
