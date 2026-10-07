"""Runtime health classification for deterministic dashboard readiness."""
from __future__ import annotations

from pathlib import Path

from vireo import __version__
from app.dashboard_data import load_dashboard_data, resolve_interim_dir
from app.bundle_validation import validate_dashboard_bundle


def classify_loaded_dashboard(data: dict) -> dict:
    ai = data.get("ai_report") or {}
    ai_available = int(ai.get("tickets_analyzed", 0) or 0) > 0 and bool(data.get("ai_by_agent"))
    warnings = []
    if not ai_available:
        warnings.append("AI diagnostics unavailable; deterministic dashboard remains functional.")
    if not data.get("stage7"):
        warnings.append("Stage 7 validation summary is not present in the dashboard bundle.")
    return {"status": "healthy" if not warnings else "degraded", "application_version": __version__,
            "deterministic_data_status": "valid", "deterministic_data": "valid",
            "agent_count": len(data.get("agents", [])),
            "ai_status": "available" if ai_available else "unavailable",
            "validated_output_count": 7, "validated_outputs": 7,
            "process_status": "not_checked", "warnings": warnings, "errors": []}


def check_dashboard_health(project_root: str | Path, interim_dir: str | Path | None = None,
                           *, require_manifest: bool = False) -> dict:
    try:
        directory = resolve_interim_dir(project_root, interim_dir)
        if not directory.is_dir():
            raise FileNotFoundError("Configured analytical output directory is missing.")
        result = classify_loaded_dashboard(load_dashboard_data(project_root, interim_dir=directory))
        if require_manifest:
            bundle = validate_dashboard_bundle(directory)
            result["provenance"] = {key: bundle["manifest"]["provenance"].get(key)
                                    for key in ("pipeline_version", "pipeline_revision", "source_snapshot_sha256",
                                                "decision_config_sha256")}
        return result
    except (FileNotFoundError, PermissionError) as exc:
        return {"status": "unhealthy", "application_version": __version__,
                "deterministic_data_status": "unavailable", "deterministic_data": "unavailable",
                "agent_count": 0, "ai_status": "unknown", "validated_output_count": 0,
                "validated_outputs": 0, "process_status": "not_checked",
                "warnings": [], "errors": [str(exc)]}
    except Exception as exc:
        return {"status": "unhealthy", "application_version": __version__,
                "deterministic_data_status": "invalid", "deterministic_data": "invalid",
                "agent_count": 0, "ai_status": "unknown", "validated_output_count": 0,
                "validated_outputs": 0, "process_status": "not_checked", "warnings": [],
                "errors": [f"Required dashboard outputs failed validation: {exc}"]}
