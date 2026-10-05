"""Descriptive transfer volume; no attribution or blame."""
from __future__ import annotations
from typing import Any

def transfer_value(raw: Any) -> tuple[int | None, str]:
    if raw in (None, ""):
        return None, "missing"
    try:
        value = int(str(raw).strip())
    except (ValueError, TypeError):
        return None, "invalid"
    return (value, "") if value >= 0 else (None, "negative")

def transfer_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [r["transfers_numeric"] for r in rows if r.get("valid_for_transfers")]
    completed = [r for r in rows if r.get("attendance_flag")]
    completed_vals = [r["transfers_numeric"] for r in completed if r.get("valid_for_transfers")]
    with_transfer = sum(v > 0 for v in valid)
    return {"transfer_valid_count": len(valid), "transfer_ineligible_count": len(rows)-len(valid),
            "total_transfers": sum(valid), "transfer_count": sum(valid), "transferred_ticket_count": with_transfer,
            "transfer_rate": with_transfer / len(valid) if valid else None,
            "transferred_ticket_rate": with_transfer / len(valid) if valid else None,
            "average_transfers_per_ticket": sum(valid) / len(valid) if valid else None,
            "completed_ticket_transfer_valid_count": len(completed_vals),
            "transfers_per_completed_ticket": sum(completed_vals) / len(completed_vals) if completed_vals else None}
