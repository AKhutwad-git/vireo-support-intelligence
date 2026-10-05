from pathlib import Path

import pyarrow.parquet as pq
import pytest

from app.dashboard_data import load_dashboard_data
from scripts.package_dashboard_data import package_dashboard_data


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "interim"
HAS_SOURCE = (SOURCE / "training_priority.parquet").is_file() and (SOURCE / "stage4_economics_report.json").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_packaged_bundle_is_minimal_and_loads_without_raw_ticket_data(tmp_path):
    target = tmp_path / "bundle"
    manifest = package_dashboard_data(SOURCE, target)
    assert manifest["contains_raw_source_data"] is False
    assert set(manifest["files"]) == {p.name for p in target.iterdir() if p.name != "deployment_manifest.json"}
    assert all(item["purpose"] and item["format"] for item in manifest["files"].values())
    assert manifest["files"]["training_priority.parquet"]["schema_version"] == 1
    assert manifest["files"]["training_priority.parquet"]["row_count"] == manifest["table_row_counts"]["training_priority.parquet"]
    assert "ticket_metrics.parquet" not in {p.name for p in target.iterdir()}
    assert "normalized_tickets.parquet" not in {p.name for p in target.iterdir()}
    table = pq.read_table(target / "training_priority.parquet")
    assert "agent_id" in table.column_names
    assert "customer_message" not in table.column_names
    data = load_dashboard_data(ROOT, interim_dir=target)
    assert len(data["agents"]) == 44
    assert data["latest_quarter"] == "2026-Q2"
    for path in target.glob("*.json"):
        assert "C:\\Users\\" not in path.read_text(encoding="utf-8")
