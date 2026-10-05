from pathlib import Path

import pytest

from app.runtime_health import check_dashboard_health, classify_loaded_dashboard
from scripts.package_dashboard_data import package_dashboard_data


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "interim"
HAS_SOURCE = (SOURCE / "training_priority.parquet").is_file()


def test_valid_deterministic_dashboard_with_ai_is_healthy():
    data = {"ai_report": {"tickets_analyzed": 1}, "ai_by_agent": {"A": {}},
            "stage7": {"status": "PASS"}, "agents": [{"agent_id": "A"}]}
    result = classify_loaded_dashboard(data)
    assert result["status"] == "healthy"
    assert result["deterministic_data_status"] == "valid"
    assert result["application_version"]


def test_no_ai_remains_degraded_with_deterministic_data():
    result = classify_loaded_dashboard({"agents": [{"agent_id": "A"}], "stage7": {"status": "PASS"}})
    assert result["status"] == "degraded"
    assert result["deterministic_data_status"] == "valid"
    assert result["ai_status"] == "unavailable"


def test_required_bundle_integrity_failure_is_unhealthy(tmp_path):
    if not HAS_SOURCE:
        pytest.skip("Generated analytical outputs are not present")
    bundle = tmp_path / "bundle"
    package_dashboard_data(SOURCE, bundle)
    with (bundle / "agent_metrics.parquet").open("ab") as stream:
        stream.write(b"corrupt")
    result = check_dashboard_health(ROOT, bundle, require_manifest=True)
    assert result["status"] == "unhealthy"
    assert result["errors"]
