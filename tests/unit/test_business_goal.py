import pytest

from vireo.policy.economics import SLA_BREACH_CREDIT_INR
from vireo.scoring.business_goal import build_sla_business_goal, build_training_budget_decision


def test_sla_goal_uses_observed_baseline_and_policy_credit_sensitivity():
    metrics = {"sla_eligible_count": 11750, "sla_breach_count": 1064}
    goal = build_sla_business_goal(metrics, reduction_percentage_points=1.0,
                                   policy_credit_per_breach_inr=SLA_BREACH_CREDIT_INR)
    assert goal == build_sla_business_goal(metrics, reduction_percentage_points=1.0,
                                           policy_credit_per_breach_inr=SLA_BREACH_CREDIT_INR)
    assert goal["baseline_rate"] == pytest.approx(1064 / 11750)
    assert goal["target_rate"] == pytest.approx(1064 / 11750 - 0.01)
    assert goal["expected_fewer_breaches_same_population"] == pytest.approx(117.5)
    assert goal["policy_credit_context_same_population_inr"] == pytest.approx(41125.0)
    assert "not causal" in goal["interpretation"]


def test_training_budget_zero_candidate_decision_reserves_exact_full_budget():
    decision = build_training_budget_decision(400000, 0, training_cost_data_available=False)
    assert decision["training_budget_inr"] == 400000
    assert decision["recommended_agent_specific_allocation_inr"] == 0
    assert decision["reserved_pending_evidence_or_costing_inr"] == 400000
    assert "not savings" in decision["interpretation"]


def test_training_budget_with_candidates_still_waits_for_missing_costs():
    decision = build_training_budget_decision(400000, 2, training_cost_data_available=False)
    assert decision["recommended_agent_specific_allocation_inr"] == 0
    assert decision["reserved_pending_evidence_or_costing_inr"] == 400000


def test_invalid_sla_denominator_is_reported_unavailable():
    assert build_sla_business_goal({"sla_eligible_count": 0, "sla_breach_count": 0})["status"] == "unavailable"
