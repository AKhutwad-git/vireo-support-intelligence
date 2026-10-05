"""First-response SLA status using policy-backed per-channel targets."""
from __future__ import annotations
from typing import Any
from .handle_time import elapsed_minutes

DEFAULT_SLA_TARGETS = {"chat": 15, "voice": 120, "social": 240, "email": 480}

def sla_for_ticket(row: dict[str, Any], targets: dict[str, int] = DEFAULT_SLA_TARGETS) -> dict[str, Any]:
    channel = str(row.get("channel") or "").casefold()
    target = targets.get(channel)
    result = {"sla_target_minutes": target, "first_response_minutes": None,
              "sla_status": "not_evaluable", "sla_breach_flag": None,
              "sla_eligibility_reason": "unknown_channel" if target is None else "missing_or_invalid_timestamp"}
    if target is None:
        return result
    minutes, issue = elapsed_minutes(row.get("created_at"), row.get("first_response_at"))
    if minutes is None:
        result["sla_eligibility_reason"] = issue
        return result
    breach = minutes > target
    result.update(first_response_minutes=minutes, sla_status="breached" if breach else "met",
                  sla_breach_flag=breach, sla_eligibility_reason="")
    return result

def sla_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [r for r in rows if r.get("sla_status") in {"met", "breached"}]
    breaches = sum(r["sla_status"] == "breached" for r in eligible)
    return {"sla_eligible_count": len(eligible), "sla_ineligible_count": len(rows)-len(eligible),
            "sla_breach_count": breaches, "sla_met_count": len(eligible)-breaches,
            "sla_breach_rate": breaches / len(eligible) if eligible else None}
