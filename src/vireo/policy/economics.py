"""Authoritative monetary standards from support-policy.pdf v3.2."""
from __future__ import annotations

CONTACT_COST_INR = {"chat": 210.0, "email": 260.0, "voice": 520.0, "social": 240.0}
BLENDED_CONTACT_COST_INR = 290.0  # reference only; channel tickets use their actual channel rate
TRANSFER_COST_INR = 305.0
SLA_BREACH_CREDIT_INR = 350.0
AGENT_STAFFING_COST_PER_HOUR_INR = 165.0  # staffing planning only; not applied to elapsed ticket time
REPLACEMENT_LOGISTICS_COST_INR = 340.0


def get_contact_cost(channel: str | None) -> float | None:
    return CONTACT_COST_INR.get((channel or "").strip().casefold())


def calculate_sla_breach_cost(breached: bool) -> float:
    return SLA_BREACH_CREDIT_INR if breached else 0.0


def calculate_transfer_cost(transfers: int | float | None) -> float:
    count = int(transfers or 0)
    if count < 0:
        raise ValueError("transfer count cannot be negative")
    return count * TRANSFER_COST_INR


def calculate_replacement_cost(unit_cost_inr: int | float | str | None) -> float | None:
    if unit_cost_inr in (None, ""):
        return None
    value = float(unit_cost_inr)
    if value < 0:
        raise ValueError("product unit cost cannot be negative")
    return value + REPLACEMENT_LOGISTICS_COST_INR
