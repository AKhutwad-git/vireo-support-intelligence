from pathlib import Path

import pyarrow.parquet as pq
import pytest

from app.dashboard_data import load_dashboard_data


ROOT = Path(__file__).resolve().parents[2]
HAS_SOURCE = (ROOT / "data" / "interim" / "training_priority.parquet").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_dashboard_flow_reconciles_priority_and_exposure_with_pipeline_outputs():
    data = load_dashboard_data(ROOT)
    stage6 = {r["agent_id"]: r for r in pq.read_table(ROOT / "data/interim/training_priority.parquet").to_pylist()}
    for row in data["agents"]:
        upstream = stage6[row["agent_id"]]
        assert row["priority_status"] == upstream["priority_status"]
        assert row["priority_rank"] == upstream["priority_rank"]
        assert row["priority_score"] == upstream["priority_score"]
    assert data["overall"]["ticket_count"] == 11750
    assert data["overall"]["completed_ticket_count"] == 11183
    assert data["exposure"]["replacement_cost_inr"] == 3415990


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_dashboard_does_not_replace_stage6_decision_rank_with_raw_metric_order():
    data = load_dashboard_data(ROOT)
    by_id = {row["agent_id"]: row for row in data["agents"]}
    source = {r["agent_id"]: r for r in pq.read_table(ROOT / "data/interim/training_priority.parquet").to_pylist()}
    assert all(by_id[agent_id]["priority_rank"] == source[agent_id]["priority_rank"] for agent_id in source)
    assert all(row["priority_status"] == "monitor" and row["priority_rank"] is None for row in data["agents"])
