"""Completed attendance is a resolved or auto-closed ticket."""
from __future__ import annotations
from typing import Any

COMPLETED_STATUSES = {"resolved", "closed"}
OPEN_STATUSES = {"open", "pending"}

def attendance_flag(status: Any) -> bool:
    return str(status or "").strip().casefold() in COMPLETED_STATUSES

def attendance_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status = [str(r.get("status") or "").strip().casefold() for r in rows]
    completed = sum(s in COMPLETED_STATUSES for s in status)
    return {"ticket_count": len(rows), "completed_ticket_count": completed,
            "resolved_ticket_count": sum(s == "resolved" for s in status),
            "closed_ticket_count": sum(s == "closed" for s in status),
            "open_pending_ticket_count": sum(s in OPEN_STATUSES for s in status),
            "attendance_ineligible_status_count": sum(s not in COMPLETED_STATUSES | OPEN_STATUSES for s in status)}
