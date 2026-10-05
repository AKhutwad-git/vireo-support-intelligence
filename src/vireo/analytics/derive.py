"""Ticket-level deterministic performance eligibility and metrics."""
from __future__ import annotations
from typing import Any
from .attendance import attendance_flag
from .csat import csat_eligibility
from .handle_time import elapsed_minutes
from .sla import DEFAULT_SLA_TARGETS, sla_for_ticket
from .transfers import transfer_value

def derive_ticket_metrics(tickets: list[dict[str, Any]], targets: dict[str, int] | None = None) -> list[dict[str, Any]]:
    targets = targets or DEFAULT_SLA_TARGETS
    output = []
    for source in tickets:
        row = dict(source)
        row["attendance_flag"] = attendance_flag(row.get("status"))
        row["valid_for_attendance"] = row["attendance_flag"]
        score_ok, score, score_reason = csat_eligibility(row)
        row["csat_score_numeric"] = score
        row["csat_eligibility_reason"] = score_reason
        row["csat_response_flag"] = score_ok
        row["csat_unexpected_status_flag"] = bool(score_ok and not row["attendance_flag"])
        # Primary survey eligibility follows policy timing: only resolved/closed tickets.
        # Keep a separate response flag and score value for anomalous open/pending rows.
        row["valid_for_csat"] = bool(score_ok and row["attendance_flag"])
        row["csat_score_invalid_flag"] = bool(row.get("csat_score") not in (None, "") and not score_ok)
        handle, handle_reason = elapsed_minutes(row.get("first_response_at"), row.get("resolved_at"))
        row["handle_time_minutes"] = handle
        row["handle_time_eligibility_reason"] = handle_reason
        row["valid_for_handle_time"] = handle is not None and row["attendance_flag"]
        if not row["valid_for_handle_time"] and handle is not None:
            row["handle_time_minutes"] = None
            row["handle_time_eligibility_reason"] = "not_completed"
        first, first_reason = elapsed_minutes(row.get("created_at"), row.get("first_response_at"))
        row["first_response_minutes"] = first
        row["first_response_eligibility_reason"] = first_reason
        row["valid_for_first_response"] = first is not None
        row.update(sla_for_ticket(row, targets))
        row["valid_for_sla"] = row["sla_status"] in {"met", "breached"}
        transfers, transfer_reason = transfer_value(row.get("transfers"))
        row["transfers_numeric"] = transfers
        row["transfer_eligibility_reason"] = transfer_reason
        row["valid_for_transfers"] = transfers is not None
        row["transfer_flag"] = transfers > 0 if transfers is not None else None
        output.append(row)
    return output
