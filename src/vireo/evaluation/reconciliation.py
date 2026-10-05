"""Independent reference calculations for Stage 2 and Stage 4 reconciliation."""
from __future__ import annotations

from datetime import datetime
from statistics import mean, median


CONTACT = {"chat": 210.0, "email": 260.0, "voice": 520.0, "social": 240.0}
TRANSFER = 305.0
SLA_CREDIT = 350.0
LOGISTICS = 340.0


def _dt(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed
    except (ValueError, TypeError):
        return None


def _score(value):
    try:
        s = int(str(value).strip())
        return s if 1 <= s <= 5 else None
    except (ValueError, TypeError):
        return None


def independent_reference(tickets, products, targets):
    """Recompute key outcomes using direct source rows and policy constants."""
    completed = [r for r in tickets if str(r.get("status") or "").strip().casefold() in {"resolved", "closed"}]
    csat = [v for r in completed if (v := _score(r.get("csat_score"))) is not None]
    handles = []
    for row in completed:
        start, end = _dt(row.get("first_response_at")), _dt(row.get("resolved_at"))
        if start and end:
            duration = (end - start).total_seconds() / 60
            if duration >= 0:
                handles.append(duration)
    breaches = 0
    sla_eligible = 0
    for row in tickets:
        target = targets.get(str(row.get("channel") or "").casefold())
        start, end = _dt(row.get("created_at")), _dt(row.get("first_response_at"))
        if target is not None and start and end:
            minutes = (end - start).total_seconds() / 60
            if minutes >= 0:
                sla_eligible += 1
                breaches += int(minutes > float(target))
    transfers = sum(int(float(r.get("transfers") or 0)) for r in tickets)
    contact_cost = sum(CONTACT[str(r.get("channel") or "").casefold()] for r in tickets)
    replacement_products = {r.get("sku"): float(r["unit_cost_inr"]) for r in products if r.get("sku") and r.get("unit_cost_inr") not in (None, "")}
    replacements = [r for r in tickets if str(r.get("replacement_issued") or "").strip().upper() == "Y"]
    replacement_cost = sum(replacement_products[r.get("product_sku")] + LOGISTICS for r in replacements)
    return {"completed_tickets": len(completed), "primary_csat_response_count": len(csat),
        "mean_csat": mean(csat) if csat else None, "handle_time_eligibility": len(handles),
        "handle_time_median_minutes": median(handles) if handles else None,
        "sla_breach_count": breaches, "sla_breach_rate": breaches / sla_eligible if sla_eligible else None,
        "transfer_count": transfers, "replacement_count": len(replacements), "replacement_cost_inr": replacement_cost,
        "refund_total_inr": sum(float(r.get("refund_amount_inr") or 0) for r in tickets),
        "contact_cost_inr": contact_cost}


def reconcile(production, reference):
    """Compare named production values against independent reference values."""
    rules = {"completed_tickets": (0.0, "exact"), "primary_csat_response_count": (0.0, "exact"),
        "mean_csat": (1e-12, "numeric"), "handle_time_eligibility": (0.0, "exact"),
        "handle_time_median_minutes": (1e-9, "numeric"), "sla_breach_count": (0.0, "exact"),
        "sla_breach_rate": (1e-12, "numeric"), "transfer_count": (0.0, "exact"),
        "replacement_count": (0.0, "exact"), "replacement_cost_inr": (0.01, "money"),
        "refund_total_inr": (0.01, "money"), "contact_cost_inr": (0.01, "money")}
    items = []
    for key, (tolerance, kind) in rules.items():
        actual, expected = production.get(key), reference.get(key)
        difference = abs(float(actual) - float(expected)) if actual is not None and expected is not None else None
        relative = difference / abs(float(expected)) if difference is not None and float(expected) != 0 else None
        passed = difference is not None and difference <= tolerance
        items.append({"metric": key, "production_value": actual, "reference_value": expected,
            "absolute_difference": difference, "relative_difference": relative,
            "tolerance": tolerance, "comparison": kind, "status": "PASS" if passed else "FAIL"})
    return {"status": "PASS" if all(r["status"] == "PASS" for r in items) else "FAIL", "checks": items}
