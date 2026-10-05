"""Ticket-level classification, strict evidence validation, and per-result fallback."""
from __future__ import annotations
import json
from .schemas import validate_ticket_result


def analyze_batch(rows, client, prompt_template, prompt_version, model, cache):
    requests, request_by_ticket, outputs, cached = [], {}, {}, 0
    for row in rows:
        raw_sources = [s for s in (row.get("analysis_customer_text"), row.get("analysis_agent_notes")) if s]
        prompt = prompt_template.format(ticket_id=row["ticket_id"], channel=row.get("channel") or "unknown",
            priority=row.get("priority") or "unknown", category=row.get("category") or "unknown",
            csat=row.get("csat_score_numeric") if row.get("valid_for_csat") else "not_eligible",
            handle_time=row.get("handle_time_minutes") if row.get("valid_for_handle_time") else "not_eligible",
            sla=row.get("sla_status") or "unknown", transfers=row.get("transfers_numeric") or 0,
            refund="yes" if _positive(row.get("refund_amount_inr")) else "no",
            replacement="yes" if row.get("replacement_issued_flag") else "no",
            peer_csat_gap=row.get("peer_adjusted_csat_gap") if row.get("peer_adjusted_csat_gap") is not None else "unavailable",
            peer_handle_time_gap=row.get("peer_adjusted_handle_time_gap") if row.get("peer_adjusted_handle_time_gap") is not None else "unavailable",
            peer_sla_gap=row.get("peer_adjusted_sla_gap") if row.get("peer_adjusted_sla_gap") is not None else "unavailable",
            customer_message=row.get("analysis_customer_text") or "[excluded: degraded or missing]",
            agent_notes=row.get("analysis_agent_notes") or "[missing]")
        key = cache.make_key(prompt, model, prompt_version)
        cached_value = cache.get(key)
        if cached_value is not None:
            outputs[row["ticket_id"]] = {"result": cached_value, "status": "cached", "actual_input_tokens": None, "actual_output_tokens": None}
            cached += 1
        else:
            requests.append({"ticket_id": row["ticket_id"], "prompt": prompt})
            request_by_ticket[row["ticket_id"]] = (key, raw_sources)
    errors = {}
    try:
        for result in client.classify_batch(requests) if requests else []:
            tid = result.get("ticket_id")
            if tid not in request_by_ticket or tid in outputs:
                errors[str(tid)] = "provider returned unknown or duplicate ticket ID"; continue
            key, sources = request_by_ticket[tid]
            if result.get("error"):
                errors[tid] = f"provider_error:{result['error']}"
                continue
            try:
                valid = validate_ticket_result(result.get("result"), tid, sources)
                try:
                    cache.set(key, valid)
                except Exception:
                    # A valid model response remains usable if persistence is unavailable.
                    pass
                outputs[tid] = {"result": valid, "status": "analyzed", "actual_input_tokens": result.get("actual_input_tokens"),
                    "actual_output_tokens": result.get("actual_output_tokens")}
            except Exception as exc:
                errors[tid] = f"invalid_model_output:{exc}"
    except Exception as exc:
        for item in requests: errors[item["ticket_id"]] = f"provider_error:{type(exc).__name__}"
    for tid in request_by_ticket:
        if tid not in outputs and tid not in errors: errors[tid] = "provider_omitted_result"
    return outputs, errors, cached


def _positive(value):
    try: return float(value or 0) > 0
    except (ValueError, TypeError): return False
