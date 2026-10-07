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
    assert "ticket_order_enriched.parquet" not in {p.name for p in target.iterdir()}
    assert manifest["product_order_analysis_included"] is True
    assert "product_sku_analysis.parquet" in manifest["files"]
    assert "order_channel_analysis.parquet" in manifest["files"]
    assert "product_lot_analysis.parquet" in manifest["files"]
    table = pq.read_table(target / "training_priority.parquet")
    assert "agent_id" in table.column_names
    assert "agent_name" in table.column_names
    assert "review_score" in table.column_names
    assert "customer_message" not in table.column_names
    assert (target / "stage6_dashboard_summary.json").is_file()
    data = load_dashboard_data(ROOT, interim_dir=target)
    assert len(data["agents"]) == 44
    assert data["latest_quarter"] == "2026-Q2"
    assert len(data["review_lists"]["bottom10_review"]) == 10
    assert len(data["review_lists"]["top5_bonus_review"]) == 5
    assert data["root_cause"]["summary"]["ticket_count"] == 11750
    assert data["root_cause"]["summary"]["order_match_counts"] == {"matched": 10817, "ambiguous": 933, "unmatched": 0}
    exposure = pq.read_table(target / "agent_product_exposure.parquet")
    assert "agent_id" in exposure.column_names
    assert "ticket_id" not in exposure.column_names
    assert "customer_id" not in exposure.column_names
    assert "order_id" not in exposure.column_names
    for path in target.glob("*.json"):
        assert "C:\\Users\\" not in path.read_text(encoding="utf-8")
