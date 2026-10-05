"""Handle time is first human response to resolution, in elapsed minutes."""
from __future__ import annotations
from datetime import datetime
from typing import Any
import math

def elapsed_minutes(start: str | None, end: str | None) -> tuple[float | None, str]:
    if not start or not end:
        return None, "missing_timestamp"
    try:
        a, b = datetime.fromisoformat(start.replace("Z", "+00:00")), datetime.fromisoformat(end.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None, "invalid_timestamp"
    minutes = (b - a).total_seconds() / 60
    return (minutes, "") if minutes >= 0 else (None, "negative_duration")

def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    low = math.floor(position); high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)

def duration_summary(rows: list[dict[str, Any]], field: str = "handle_time_minutes", eligible: str = "valid_for_handle_time", prefix: str = "handle_time") -> dict[str, Any]:
    vals = [float(r[field]) for r in rows if r.get(eligible) and r.get(field) is not None]
    n = len(vals)
    return {f"{prefix}_eligible_count": n, f"{prefix}_ineligible_count": len(rows) - n,
            f"{prefix}_mean": sum(vals) / n if n else None, f"{prefix}_median": percentile(vals, .5),
            f"{prefix}_p75": percentile(vals, .75), f"{prefix}_p90": percentile(vals, .90)}
