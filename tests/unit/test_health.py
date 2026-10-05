from pathlib import Path

from app.runtime_health import check_dashboard_health
import pytest


ROOT = Path(__file__).resolve().parents[2]
HAS_SOURCE = (ROOT / "data" / "interim" / "training_priority.parquet").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_current_no_ai_outputs_are_degraded_not_unhealthy():
    result = check_dashboard_health(ROOT)
    assert result["status"] == "degraded"
    assert result["deterministic_data"] == "valid"
    assert result["ai_status"] == "unavailable"
    assert result["errors"] == []


def test_missing_output_directory_is_unhealthy(tmp_path):
    result = check_dashboard_health(tmp_path, tmp_path / "missing")
    assert result["status"] == "unhealthy"
    assert result["deterministic_data"] == "unavailable"
    assert result["errors"]


def test_corrupt_required_schema_is_unhealthy(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq

    outputs = tmp_path / "outputs"
    outputs.mkdir()
    pq.write_table(pa.table({"agent_id": ["A"]}), outputs / "training_priority.parquet")
    result = check_dashboard_health(tmp_path, outputs)
    assert result["status"] == "unhealthy"
    assert result["deterministic_data"] == "invalid"
    assert "priority_status" in result["errors"][0]
