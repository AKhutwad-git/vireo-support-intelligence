"""Planted-effect decision-engine checks; synthetic outcomes are not real-agent evidence."""
from __future__ import annotations

from copy import deepcopy

from vireo.scoring.priority import build_priority_rows


def _case(agent_id="S1", tier="1", adverse=True, observations=100, peer_count=6, group=None):
    if group is None:
        group = f"tier={tier}|team=synthetic"
    row = {"agent_id": agent_id, "agent_team": "Synthetic", "agent_tier": tier,
        "ticket_count": observations, "comparison_group": group, "peer_supported": True,
        "peer_agent_count": peer_count, "comparison_status": "comparable", "stability_flag": "no_clear_shift_detected",
        "csat_gap": -0.9 if adverse else 0.0, "csat_gap_ci_lower": -1.2 if adverse else -0.15,
        "csat_gap_ci_upper": -0.6 if adverse else 0.15, "csat_gap_interval_direction": "below_zero" if adverse else "overlaps_zero",
        "csat_eligible_count": observations, "csat_adjustment_coverage_rate": 1.0,
        "handle_time_gap": 60.0 if adverse else 0.0, "peer_handle_time_mean": 120.0,
        "handle_time_gap_ci_lower": 30.0 if adverse else -15.0, "handle_time_gap_ci_upper": 90.0 if adverse else 15.0,
        "handle_time_gap_interval_direction": "above_zero" if adverse else "overlaps_zero",
        "handle_time_eligible_count": observations, "handle_time_adjustment_coverage_rate": 1.0,
        "sla_gap": 0.12 if adverse else 0.0, "sla_gap_ci_lower": 0.06 if adverse else -0.03,
        "sla_gap_ci_upper": 0.18 if adverse else 0.03, "sla_gap_interval_direction": "above_zero" if adverse else "overlaps_zero",
        "sla_eligible_count": observations, "sla_adjustment_coverage_rate": 1.0}
    return row


def _inputs():
    comparisons = []
    metrics = []
    economics = []
    for i in range(6):
        aid = f"S{i+1}"
        full = _case(aid, adverse=(i == 0))
        full["period_type"] = "full_available_period"
        comparisons.append(full)
        metrics.append({"agent_id": aid, "ticket_count": full["ticket_count"], "mean_csat": 3.2,
                        "handle_time_mean": 120., "sla_breach_rate": .1})
        economics.append({"agent_id": aid, "operational_cost_exposure_inr": 1000.})
        for q in range(4):
            quarter = _case(aid, adverse=(i == 0 and q < 2))
            quarter.update(period_type="quarter", period=f"2025-Q{q+1}")
            comparisons.append(quarter)
    return comparisons, metrics, economics


def synthetic_decision_scenarios(config):
    comp, metrics, economics = _inputs()
    normal_ai = []
    baseline = build_priority_rows(comp, metrics, economics, normal_ai, "unavailable", config)
    outputs = {r["agent_id"]: r for r in baseline}
    records = []

    def add(name, expected, actual, passed, reason):
        records.append({"scenario": name, "expected_behavior": expected, "actual_behavior": actual,
                        "status": "PASS" if passed else "FAIL", "reason": reason, "data_type": "synthetic"})

    add("strong_persistent_effect", "training_candidate", outputs["S1"]["priority_status"] + ":" + outputs["S1"]["priority_band"],
        outputs["S1"]["priority_status"] == "training_candidate" and outputs["S1"]["priority_band"] == "high",
        "Planted adverse CSAT, handle-time and SLA intervals with ample evidence and two persistent adverse quarters.")

    tiny_comp = deepcopy(comp)
    tiny_full = next(r for r in tiny_comp if r["agent_id"] == "S1" and r["period_type"] == "full_available_period")
    tiny_full.update(ticket_count=8, csat_eligible_count=4, handle_time_eligible_count=8, sla_eligible_count=8)
    tiny = {r["agent_id"]: r for r in build_priority_rows(tiny_comp, metrics, economics, [], "unavailable", config)}["S1"]
    add("tiny_sample_extreme_gap", "not_rankable:insufficient_evidence", tiny["priority_status"] + ":" + ",".join(tiny["eligibility_gates"]),
        tiny["priority_status"] == "not_rankable" and "insufficient_evidence" in tiny["eligibility_gates"],
        "Extreme point gaps do not bypass the minimum-observation gate.")

    one_period_comp = deepcopy(comp)
    for r in one_period_comp:
        if r["agent_id"] == "S1" and r["period_type"] == "quarter" and r["period"] not in {"2025-Q1"}:
            r["csat_gap_ci_lower"], r["csat_gap_ci_upper"] = .1, .5
            r["handle_time_gap_ci_lower"], r["handle_time_gap_ci_upper"] = -30., -5.
            r["sla_gap_ci_lower"], r["sla_gap_ci_upper"] = -.1, -.01
    one_period = {r["agent_id"]: r for r in build_priority_rows(one_period_comp, metrics, economics, [], "unavailable", config)}["S1"]
    add("one_period_signal", "not high priority", one_period["priority_band"],
        one_period["priority_band"] != "high", "A single adverse quarter plus otherwise favorable periods cannot receive the persistent high band.")

    tier_comp = deepcopy(comp)
    tier_full = next(r for r in tier_comp if r["agent_id"] == "S1" and r["period_type"] == "full_available_period")
    tier_full["agent_tier"] = "2"
    tier = {r["agent_id"]: r for r in build_priority_rows(tier_comp, metrics, economics, [], "unavailable", config)}["S1"]
    add("tier_mismatch", "blocked by invalid_tier_peer", tier["priority_status"] + ":" + ",".join(tier["eligibility_gates"]),
        "invalid_tier_peer" in tier["eligibility_gates"] and tier["priority_status"] == "not_rankable",
        "The stored peer-group key says Tier 1 while the agent context says Tier 2.")

    ai = build_priority_rows(comp, metrics, economics, [], "unavailable", config)
    add("ai_unavailable", "same numeric result; AI unavailable", "unavailable" if all(r["ai_evidence_status"] == "unavailable" for r in ai) else "unexpected",
        all(a["priority_score"] == b["priority_score"] for a, b in zip(baseline, ai)),
        "No AI diagnostics are present; deterministic scores remain unchanged.")

    conflict_comp = deepcopy(comp)
    conflict_full = next(r for r in conflict_comp if r["agent_id"] == "S1" and r["period_type"] == "full_available_period")
    conflict_full.update(handle_time_gap=-30., handle_time_gap_ci_lower=-50., handle_time_gap_ci_upper=-10.,
                         handle_time_gap_interval_direction="below_zero")
    conflict = {r["agent_id"]: r for r in build_priority_rows(conflict_comp, metrics, economics, [], "unavailable", config)}["S1"]
    add("conflicting_outcomes", "mixed-performance state", conflict["diagnostic_state"],
        conflict["diagnostic_state"] == "mixed_performance", "Adverse CSAT/SLA and favorable handle time remain visible together.")

    cost_comp = deepcopy(comp)
    cost_normal = {r["agent_id"]: r for r in build_priority_rows(cost_comp, metrics,
        [{**e, "operational_cost_exposure_inr": 99_000_000.} if e["agent_id"] == "S2" else e for e in economics],
        [], "unavailable", config)}["S2"]
    normal = outputs["S2"]
    add("high_cost_normal_quality", "no automatic priority from exposure", cost_normal["priority_status"],
        cost_normal["priority_status"] == normal["priority_status"] and cost_normal["priority_score"] == normal["priority_score"],
        "Economic exposure is context only and is excluded from the score.")

    repeat1 = build_priority_rows(comp, metrics, economics, [], "unavailable", config)
    repeat2 = build_priority_rows(comp, metrics, economics, [], "unavailable", config)
    add("harmless_perturbation_reproducibility", "identical deterministic decisions", "identical" if repeat1 == repeat2 else "different",
        repeat1 == repeat2, "Repeated evaluation with identical inputs/configuration returns identical records.")
    return records
