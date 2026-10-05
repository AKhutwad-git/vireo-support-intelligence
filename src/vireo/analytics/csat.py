"""CSAT eligibility and descriptive aggregation."""
from __future__ import annotations
from typing import Any

def csat_eligibility(row: dict[str, Any]) -> tuple[bool, int | None, str]:
    raw = row.get("csat_score")
    if raw in (None, ""):
        return False, None, "no_response"
    try:
        score = int(str(raw).strip())
    except (ValueError, TypeError):
        return False, None, "invalid_score"
    if score < 1 or score > 5:
        return False, None, "score_out_of_range"
    return True, score, ""

def csat_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [r for r in rows if r.get("attendance_flag")]
    scores = [r["csat_score_numeric"] for r in rows if r.get("valid_for_csat")]
    completed_scores = [r["csat_score_numeric"] for r in rows if r.get("valid_for_csat") and r.get("attendance_flag")]
    n = len(scores)
    populated_scores = sum(bool(r.get("csat_response_flag")) for r in rows)
    out = {"ticket_count": len(rows), "completed_ticket_count": len(completed),
           "csat_response_count": n, "csat_completed_response_count": len(completed_scores),
           "csat_populated_valid_score_count": populated_scores,
           "csat_response_rate": len(completed_scores) / len(completed) if completed else None,
           "mean_csat": sum(scores) / n if n else None,
           "csat_response_on_noncompleted_count": sum(bool(r.get("csat_unexpected_status_flag")) for r in rows)}
    for score in range(1, 6):
        out[f"csat_score_{score}_count"] = sum(s == score for s in scores)
    out["csat_invalid_score_count"] = sum(r.get("csat_eligibility_reason") == "invalid_score" or r.get("csat_eligibility_reason") == "score_out_of_range" for r in rows)
    return out
