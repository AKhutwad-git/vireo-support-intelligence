"""Runtime health classification for deterministic dashboard readiness."""
from __future__ import annotations

from pathlib import Path

from vireo import __version__
from app.dashboard_data import load_dashboard_data, resolve_interim_dir


def classify_loaded_dashboard(data: dict) -> dict:
    ai = data.get("ai_report") or {}
    ai_available = int(ai.get("tickets_analyzed", 0) or 0) > 0 and bool(data.get("ai_by_agent"))
    warnings = []
    if not ai_available:
        warnings.append("AI diagnostics unavailable; deterministic dashboard remains functional.")
    if not data.get("stage7"):
        warnings.append("Stage 7 validation summary is not present in the dashboard bundle.")
    return {"status": "healthy" if not warnings else "degraded", "application_version": __version__,
            "deterministic_data": "valid", "agent_count": len(data.get("agents", [])),
            "ai_status": "available" if ai_available else "unavailable", "warnings": warnings, "errors": []}


def check_dashboard_health(project_root: str | Path, interim_dir: str | Path | None = None) -> dict:
    try:
        directory = resolve_interim_dir(project_root, interim_dir)
        if not directory.is_dir():
            raise FileNotFoundError("Configured analytical output directory is missing.")
        result = classify_loaded_dashboard(load_dashboard_data(project_root, interim_dir=directory))
        result["validated_outputs"] = 6
        return result
    except (FileNotFoundError, PermissionError) as exc:
        return {"status": "unhealthy", "application_version": __version__, "deterministic_data": "unavailable",
                "ai_status": "unknown", "warnings": [], "errors": [str(exc)]}
    except Exception as exc:
        return {"status": "unhealthy", "application_version": __version__, "deterministic_data": "invalid",
                "ai_status": "unknown", "warnings": [], "errors": [f"Required dashboard outputs failed validation: {exc}"]}
