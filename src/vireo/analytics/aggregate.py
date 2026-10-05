"""Shared metric aggregation primitives."""
from __future__ import annotations
from typing import Any
from .attendance import attendance_summary
from .csat import csat_summary
from .handle_time import duration_summary, percentile
from .sla import sla_summary
from .transfers import transfer_summary

def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = attendance_summary(rows)
    out.update(csat_summary(rows))
    out.update(duration_summary(rows))
    first = [float(r["first_response_minutes"]) for r in rows if r.get("valid_for_first_response")]
    out.update(first_response_eligible_count=len(first), first_response_ineligible_count=len(rows)-len(first),
               first_response_mean=sum(first)/len(first) if first else None,
               first_response_median=percentile(first, .5) if first else None)
    out.update(sla_summary(rows))
    out.update(transfer_summary(rows))
    out.update(text_degraded_ticket_count=sum(r.get("text_quality_flag") == "degraded" for r in rows),
               signup_anomaly_ticket_count=sum(bool(r.get("signup_anomaly_flag")) for r in rows),
               product_prelaunch_ticket_count=sum(bool(r.get("product_prelaunch_anomaly_flag")) for r in rows),
               reconciliation_candidate_count=sum(bool(r.get("reconciliation_flag")) for r in rows),
               unmatched_roster_ticket_count=sum(r.get("agent_assignment_flag") != "matched" for r in rows))
    return out
