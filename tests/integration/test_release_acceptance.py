from pathlib import Path

import pytest

from app.release_acceptance import evaluate_release_acceptance
from scripts.package_dashboard_data import package_dashboard_data


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "interim"
HAS_SOURCE = (SOURCE / "training_priority.parquet").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_release_requires_tests_bundle_health_and_ci_evidence(tmp_path):
    bundle = tmp_path / "bundle"
    package_dashboard_data(SOURCE, bundle)
    evidence = {key: "PASS" for key in ("tests", "pipeline", "stage7", "docker_build", "container_start", "ci")}
    health = {"status": "degraded", "deterministic_data_status": "valid", "process_status": "alive"}
    assert evaluate_release_acceptance(evidence, bundle, health)["accepted"] is True

    evidence["ci"] = "PENDING"
    result = evaluate_release_acceptance(evidence, bundle, health)
    assert result["accepted"] is False
    assert "ci evidence is not PASS" in result["failures"]

    health["deterministic_data_status"] = "invalid"
    assert evaluate_release_acceptance({**evidence, "ci": "PASS"}, bundle, health)["accepted"] is False
