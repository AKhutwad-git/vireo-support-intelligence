"""Small, explicit release gate for operational acceptance evidence."""
from __future__ import annotations

from pathlib import Path

from app.bundle_validation import validate_dashboard_bundle


def evaluate_release_acceptance(evidence: dict, bundle_dir: str | Path, health: dict) -> dict:
    failures = []
    for key in ("tests", "pipeline", "stage7", "docker_build", "container_start", "ci"):
        if evidence.get(key) != "PASS":
            failures.append(f"{key} evidence is not PASS")
    try:
        bundle = validate_dashboard_bundle(bundle_dir)
    except Exception as exc:
        bundle = None
        failures.append(f"bundle validation failed: {exc}")
    if health.get("status") not in {"healthy", "degraded"}:
        failures.append("runtime health is not healthy/degraded")
    if health.get("deterministic_data_status", health.get("deterministic_data")) != "valid":
        failures.append("runtime deterministic data is not valid")
    if health.get("process_status", health.get("process")) != "alive":
        failures.append("application process is not alive")
    return {"accepted": not failures, "failures": failures,
            "application_version": bundle.get("application_version") if bundle else None,
            "agent_count": bundle.get("agent_count") if bundle else None}
