from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from app.dashboard_data import load_dashboard_data


ROOT = Path(__file__).resolve().parents[2]
HAS_SOURCE = (ROOT / "data" / "interim" / "training_priority.parquet").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_required_dashboard_outputs_load_and_schemas_match():
    data = load_dashboard_data(ROOT)
    assert len(data["agents"]) == 44
    assert all(row.get("agent_name") for row in data["agents"])
    assert all(row["review_score"] is not None for row in data["review_lists"]["bottom10_review"] + data["review_lists"]["top5_bonus_review"])
    assert data["latest_quarter"] == "2026-Q2"
    assert data["priority_counts"] == {"monitor": 44}
    assert all(row["priority_status"] == "monitor" for row in data["agents"])
    assert len(data["review_lists"]["bottom10_review"]) == 10
    assert len(data["review_lists"]["top5_bonus_review"]) == 5
    assert data["stage6"]["training_budget_decision"]["recommended_agent_specific_allocation_inr"] == 0
    assert data["stage6"]["training_budget_decision"]["reserved_pending_evidence_or_costing_inr"] == 400000
    assert data["stage6"]["business_goal"]["eligible_ticket_count"] == 11750


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_missing_optional_ai_diagnostics_does_not_break_data_preparation(tmp_path):
    import shutil

    shutil.copytree(ROOT / "data" / "interim", tmp_path / "data" / "interim")
    (tmp_path / "data" / "interim" / "ai_agent_diagnostics.parquet").unlink()
    data = load_dashboard_data(tmp_path)
    assert len(data["agents"]) == 44
    assert all(row["ai_diagnostics"] is None for row in data["agents"])
    assert len(data["review_lists"]["bottom10_review"]) == 10


def test_invalid_required_schema_fails_with_field_name(tmp_path):
    from app.dashboard_data import REQUIRED_FIELDS

    interim = tmp_path / "data" / "interim"
    interim.mkdir(parents=True)
    pq.write_table(pa.table({"agent_id": ["A"]}), interim / "training_priority.parquet")
    with pytest.raises(ValueError, match="priority_status"):
        load_dashboard_data(tmp_path)
