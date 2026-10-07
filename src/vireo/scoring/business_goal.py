"""Reproducible operational target and training-budget decision summaries."""
from __future__ import annotations

from math import isfinite


def build_sla_business_goal(overall_metrics: dict, *, reduction_percentage_points: float = 1.0,
                            policy_credit_per_breach_inr: float = 350.0) -> dict:
    """Build an explicitly proposed SLA target and same-population sensitivity."""
    eligible = int(overall_metrics.get("sla_eligible_count") or 0)
    breaches = int(overall_metrics.get("sla_breach_count") or 0)
    reduction = float(reduction_percentage_points) / 100.0
    credit = float(policy_credit_per_breach_inr)
    if (eligible <= 0 or breaches < 0 or breaches > eligible or not isfinite(reduction)
            or reduction < 0 or reduction > 100 or not isfinite(credit) or credit < 0):
        return {"status": "unavailable", "reason": "A valid eligible-ticket denominator and breach count are required."}
    baseline = breaches / eligible
    applied_reduction = min(baseline, reduction)
    target = baseline - applied_reduction
    expected_fewer = applied_reduction * eligible
    return {
        "status": "proposed_operational_target",
        "metric": "Resolver-associated first-response SLA breach rate",
        "baseline_rate": baseline,
        "baseline_breaches": breaches,
        "eligible_ticket_count": eligible,
        "target_rate": target,
        "target_reduction_percentage_points": applied_reduction * 100.0,
        "expected_fewer_breaches_same_population": expected_fewer,
        "policy_credit_per_breach_inr": credit,
        "policy_credit_context_same_population_inr": expected_fewer * credit,
        "formula": "baseline = observed breaches / observed SLA-eligible tickets; target = max(0, baseline - 1 percentage point); same-population credit context = eligible tickets * (baseline - target) * ₹350 per breach.",
        "interpretation": "Analyst-proposed operational target and hypothetical policy-credit context on the observed denominator; not causal attribution, a forecast, realized savings, or a guaranteed credit reduction.",
    }


def build_training_budget_decision(training_budget_inr: float, training_candidate_count: int,
                                   training_cost_data_available: bool = False) -> dict:
    """Avoid allocating training funds without evidence and unit-cost inputs."""
    budget = float(training_budget_inr)
    candidates = int(training_candidate_count)
    if budget < 0 or candidates < 0:
        raise ValueError("Budget and candidate count must be non-negative")
    if candidates == 0:
        allocation = 0.0
        reserve = budget
        rationale = "No agent meets the current evidence gate; reserve the budget pending stronger evidence or targeted process investigation."
    elif not training_cost_data_available:
        allocation = 0.0
        reserve = budget
        rationale = "Candidates exist, but training-cost data is unavailable; reserve the budget until a costed, reviewed plan exists."
    else:
        allocation = None
        reserve = None
        rationale = "A costed allocation requires a separately reviewed plan; the evidence engine does not allocate funds automatically."
    return {"training_budget_inr": budget, "training_candidate_count": candidates,
            "recommended_agent_specific_allocation_inr": allocation,
            "reserved_pending_evidence_or_costing_inr": reserve,
            "training_cost_data_available": bool(training_cost_data_available),
            "rationale": rationale,
            "interpretation": "Budget decision aid only; reserved funds are not savings."}
