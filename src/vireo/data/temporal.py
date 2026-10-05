"""Source-aware timestamp parsing and effective-dated roster lookup."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any

IST = ZoneInfo("Asia/Kolkata")


def normalize_ticket_timestamp(value: str | None, source_system: str, field: str) -> tuple[str | None, bool]:
    """Return UTC ISO timestamp; legacy reconstructed resolution values are UTC, others IST."""
    if not value:
        return None, False
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    applied = parsed.tzinfo is None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc if source_system == "legacy_fd" and field == "resolved_at" else IST)
    return parsed.astimezone(timezone.utc).isoformat(), applied


def assign_roster(ticket: dict[str, Any], roster: list[dict[str, Any]], timestamp_field: str = "resolved_at") -> dict[str, Any] | None:
    """Select the agent_id roster interval containing the assignment timestamp (UTC ISO)."""
    agent_id = ticket.get("agent_id")
    stamp = ticket.get(timestamp_field)
    if not agent_id or not stamp:
        return None
    when = datetime.fromisoformat(stamp.replace("Z", "+00:00")).date()
    matches = []
    for row in roster:
        if row.get("agent_id") != agent_id:
            continue
        start = datetime.fromisoformat(row["from_date"]).date()
        end = datetime.fromisoformat(row["to_date"]).date() if row.get("to_date") else None
        if start <= when and (end is None or when <= end):
            matches.append(row)
    if len(matches) > 1:
        raise ValueError(f"Overlapping roster intervals for agent {agent_id} at {stamp}")
    return matches[0] if matches else None
