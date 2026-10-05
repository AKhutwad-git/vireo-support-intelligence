"""Versioned prompt loading and compact request assembly."""
from __future__ import annotations
from pathlib import Path
import yaml


def load_prompts(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or not data.get("issue_classification_v1"):
        raise ValueError(f"Prompt catalog missing issue_classification_v1: {path}")
    return data


def ticket_prompt(row, template):
    # Stage 2-4 metrics are compact context only. Customer and agent text are clipped.
    return template.format(ticket_id=row["ticket_id"], channel=row.get("channel") or "unknown",
        priority=row.get("priority") or "unknown", category=row.get("category") or "unknown",
        csat=row.get("csat_score_numeric") if row.get("valid_for_csat") else "not_eligible",
        handle_time=row.get("handle_time_minutes") if row.get("valid_for_handle_time") else "not_eligible",
        sla=row.get("sla_status") or "unknown", transfers=row.get("transfers_numeric") or 0,
        peer_csat_gap=row.get("peer_adjusted_csat_gap") if row.get("peer_adjusted_csat_gap") is not None else "unavailable",
        peer_handle_time_gap=row.get("peer_adjusted_handle_time_gap") if row.get("peer_adjusted_handle_time_gap") is not None else "unavailable",
        peer_sla_gap=row.get("peer_adjusted_sla_gap") if row.get("peer_adjusted_sla_gap") is not None else "unavailable",
        refund="yes" if (_num(row.get("refund_amount_inr")) or 0) > 0 else "no",
        replacement="yes" if row.get("replacement_issued_flag") else "no",
        customer_message=row.get("analysis_customer_text") or "[excluded: degraded or missing]",
        agent_notes=row.get("analysis_agent_notes") or "[missing]")


def _num(value):
    try: return float(value) if value not in (None, "") else None
    except (ValueError, TypeError): return None
