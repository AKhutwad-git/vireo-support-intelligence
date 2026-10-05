"""Transparent, tier-safe training-priority decisions from Stage 2-5 artifacts."""
from __future__ import annotations

from collections import Counter, defaultdict
from math import isfinite


METRICS = {
    "csat": {"gap": "csat_gap", "lower": "csat_gap_ci_lower", "upper": "csat_gap_ci_upper",
             "count": "csat_eligible_count", "coverage": "csat_adjustment_coverage_rate", "weight": "csat",
             "direction": -1, "scale": "csat_gap_scale"},
    "handle_time": {"gap": "handle_time_gap", "lower": "handle_time_gap_ci_lower", "upper": "handle_time_gap_ci_upper",
                    "count": "handle_time_eligible_count", "coverage": "handle_time_adjustment_coverage_rate", "weight": "handle_time",
                    "direction": 1, "scale": "handle_time_relative_gap_scale"},
    "sla": {"gap": "sla_gap", "lower": "sla_gap_ci_lower", "upper": "sla_gap_ci_upper",
            "count": "sla_eligible_count", "coverage": "sla_adjustment_coverage_rate", "weight": "sla",
            "direction": 1, "scale": "sla_gap_scale"},
}


def _num(value):
    try:
        v = float(value)
        return v if isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _adverse(metric, row, require_interval=True):
    spec = METRICS[metric]
    gap = _num(row.get(spec["gap"]))
    if gap is None:
        return False
    if not require_interval:
        return gap * spec["direction"] > 0
    lower, upper = _num(row.get(spec["lower"])), _num(row.get(spec["upper"]))
    if lower is None or upper is None:
        return False
    return upper < 0 if metric == "csat" else lower > 0


def _severity(metric, row, config):
    spec = METRICS[metric]
    gap = _num(row.get(spec["gap"]))
    if gap is None:
        return 0.0
    if metric == "handle_time":
        baseline = _num(row.get("peer_handle_time_mean"))
        if baseline is None or baseline <= 0:
            return 0.0
        adverse = gap / baseline
    else:
        adverse = gap * spec["direction"]
    scale = float(config.get(spec["scale"], 0.5 if metric == "csat" else 0.25 if metric == "handle_time" else 0.05))
    return min(1.0, max(0.0, adverse / scale)) if scale > 0 else 0.0


def _stability(metric, quarters):
    spec = METRICS[metric]
    directions = []
    for q in quarters:
        if q.get("period_type") != "quarter":
            continue
        if not q.get("peer_supported") or not _num(q.get(spec["gap"])):
            continue
        lower, upper = _num(q.get(spec["lower"])), _num(q.get(spec["upper"]))
        if metric == "csat":
            if upper is not None and upper < 0: directions.append("adverse")
            elif lower is not None and lower > 0: directions.append("favorable")
            else: directions.append("uncertain")
        else:
            if lower is not None and lower > 0: directions.append("adverse")
            elif upper is not None and upper < 0: directions.append("favorable")
            else: directions.append("uncertain")
    adverse = directions.count("adverse")
    favorable = directions.count("favorable")
    if adverse >= 2:
        state = "persistent"
    elif adverse and favorable:
        state = "mixed"
    elif adverse == 1:
        state = "single_period"
    elif len(directions) < 2:
        state = "insufficient_history"
    else:
        state = "no_clear_adverse_period_signal"
    return {"state": state, "adverse_quarters": adverse, "favorable_quarters": favorable,
            "observed_quarters": len(directions), "source_stability_flag": None}


def _evidence_strength(row, config):
    min_count = int(config.get("minimum_metric_observations", 30))
    counts = [_num(row.get(s["count"])) for s in METRICS.values()]
    coverage = [_num(row.get(s["coverage"])) for s in METRICS.values()]
    peer_agents = int(row.get("peer_agent_count") or 0)
    if any(c is None for c in counts) or min(counts, default=0) < min_count or any(v is None for v in coverage):
        return "LOW"
    if min(coverage, default=0) < float(config.get("minimum_adjustment_coverage", 0.7)) or peer_agents < int(config.get("minimum_peer_agents", 3)):
        return "LOW"
    if min(counts, default=0) >= int(config.get("high_evidence_observations", 60)) and peer_agents >= int(config.get("high_evidence_peer_agents", 5)):
        return "HIGH"
    return "MEDIUM"


def build_priority_rows(comparisons, agent_metrics, economics, ai_rows, ai_status, config):
    """Return one transparent decision row per agent, with ranks only for gated candidates."""
    by_id = defaultdict(list)
    for row in comparisons:
        if row.get("period_type") == "full_available_period":
            by_id[row.get("agent_id")].append(row)
    metrics_by_id = {r["agent_id"]: r for r in agent_metrics}
    econ_by_id = {r["agent_id"]: r for r in economics}
    ai_by_id = {r["agent_id"]: r for r in ai_rows if r.get("agent_id")}
    quarters_by_id = defaultdict(list)
    for row in comparisons:
        if row.get("period_type") == "quarter":
            quarters_by_id[row.get("agent_id")].append(row)

    rows = []
    for agent_id in sorted(metrics_by_id):
        candidates = by_id.get(agent_id, [])
        comparable = [r for r in candidates if r.get("peer_supported") and r.get("comparison_status") != "no_effective_assignment"]
        base = max(comparable or candidates, key=lambda r: int(r.get("ticket_count") or 0), default={})
        metric_row = metrics_by_id[agent_id]
        econ = econ_by_id.get(agent_id, {})
        gates, limitations = [], []
        if not base or not base.get("peer_supported") or not base.get("comparison_group"):
            gates.append("no_comparable_peer")
        elif f"tier={str(base.get('agent_tier'))}" not in str(base.get("comparison_group")):
            gates.append("invalid_tier_peer")
        if int(base.get("ticket_count") or 0) < int(config.get("minimum_agent_tickets", 30)):
            gates.append("insufficient_evidence")
        if any(_num(base.get(s["count"])) is None or _num(base.get(s["count"])) < int(config.get("minimum_metric_observations", 30)) for s in METRICS.values()):
            gates.append("insufficient_evidence")
        coverages = [_num(base.get(s["coverage"])) for s in METRICS.values()]
        if any(v is None or v < float(config.get("minimum_adjustment_coverage", 0.7)) for v in coverages):
            gates.append("data_quality_restricted")
        total_tickets = int(metric_row.get("ticket_count") or 0)
        matched_tickets = int(base.get("ticket_count") or 0)
        roster_coverage = matched_tickets / total_tickets if total_tickets else 0.0
        if roster_coverage < float(config.get("minimum_roster_coverage", 0.7)):
            gates.append("data_quality_restricted")
        source_stability = base.get("stability_flag")
        quarter_rows = quarters_by_id.get(agent_id, [])
        stability = {m: _stability(m, quarter_rows) for m in METRICS}
        use_intervals = bool(config.get("require_interval_excludes_zero", True))
        metric_directions = {m: "concern" if _adverse(m, base, use_intervals) else "favorable" if _favorable(m, base) and use_intervals else "uncertain" for m in METRICS}
        concern_count = sum(v == "concern" for v in metric_directions.values())
        favorable_count = sum(v == "favorable" for v in metric_directions.values())
        diagnostic_state = ("mixed_performance" if concern_count and favorable_count else
            "multiple_concerns" if concern_count > 1 else
            "csat_concern" if metric_directions["csat"] == "concern" else
            "handle_time_concern" if metric_directions["handle_time"] == "concern" else
            "sla_concern" if metric_directions["sla"] == "concern" else "no_clear_concern")
        adverse_quarters = max((v["adverse_quarters"] for v in stability.values()), default=0)
        stability_state = ("persistent" if adverse_quarters >= 2 else "mixed" if any(v["state"] == "mixed" for v in stability.values())
                           else "single_period" if adverse_quarters == 1 else "insufficient_history" if all(v["state"] == "insufficient_history" for v in stability.values())
                           else "no_clear_adverse_period_signal")
        source_stability_restricted = source_stability == "variable_across_quarters"
        if source_stability_restricted:
            gates.append("unstable")
        evidence = _evidence_strength(base, config)
        uncertainty = "all_intervals_overlap_zero" if all(base.get(s["gap"] + "_interval_direction") == "overlaps_zero" for s in METRICS.values()) else "mixed_or_insufficient_intervals"
        weights = config.get("metric_weights", {"csat": 0.4, "handle_time": 0.35, "sla": 0.25})
        total_weight = sum(float(weights.get(m, 0)) for m in METRICS)
        score = 0.0
        if total_weight:
            score = 100 * sum(float(weights.get(m, 0)) * _severity(m, base, config) * int(_adverse(m, base, use_intervals)) for m in METRICS) / total_weight
        evidence_factor = {"HIGH": 1.0, "MEDIUM": 0.75, "LOW": 0.4, "INSUFFICIENT": 0.0}[evidence]
        stability_factors = config.get("stability_factors", {"persistent": 1.0, "mixed": 0.8, "single_period": 0.65,
            "no_clear_adverse_period_signal": 0.55, "insufficient_history": 0.4})
        stability_factor = float(stability_factors.get(stability_state, 0.4))
        score = round(score * evidence_factor * stability_factor, 2)
        eligible = not gates
        if not eligible:
            priority_status = "not_rankable"
            band = "not_rankable"
        elif not any(metric_directions[m] == "concern" for m in METRICS) or score < float(config.get("medium_priority_score", 25)):
            priority_status, band = "monitor", "monitor"
        elif score >= float(config.get("high_priority_score", 55)) and stability_state == "persistent":
            priority_status, band = "training_candidate", "high"
        elif score >= float(config.get("medium_priority_score", 25)):
            priority_status, band = "training_candidate", "medium"
        else:
            priority_status, band = "monitor", "monitor"
        ai = ai_by_id.get(agent_id, {})
        if ai_status == "available" and ai:
            ai_evidence_status = "available"
        elif ai_status == "failed":
            ai_evidence_status = "failed"
        elif ai_status == "partial":
            ai_evidence_status = "partial"
        else:
            ai_evidence_status = "unavailable"
        reasons = _reasons(metric_directions, gates, evidence, stability_state, priority_status)
        if ai_evidence_status != "available":
            limitations.append("No validated real-model diagnostic evidence was available; this does not reduce deterministic priority.")
        if roster_coverage < 1:
            limitations.append(f"Peer-comparison tickets cover {roster_coverage:.1%} of this agent's tickets; unmatched context is retained outside the peer comparison.")
        limitations.extend(["Adjusted intervals are approximate and overlap can reflect limited precision.",
                            "Observed differences are not causal evidence about agent behavior."])
        raw_ranks = {"csat_low_is_worse": None, "handle_time_high_is_worse": None, "sla_high_is_worse": None}
        rows.append({"agent_id": agent_id, "team": base.get("agent_team"), "tier": base.get("agent_tier"),
            "peer_group": base.get("comparison_group"), "comparison_group": base.get("comparison_group"),
            "priority_status": priority_status, "priority_rank": None, "priority_band": band,
            "priority_score": score, "eligibility_gates": sorted(set(gates)), "primary_signal": _primary_signal(metric_directions, base),
            "secondary_signal": _secondary_signal(metric_directions, base), "csat_gap": _num(base.get("csat_gap")),
            "handle_time_gap": _num(base.get("handle_time_gap")), "sla_gap": _num(base.get("sla_gap")),
            "csat_gap_ci_lower": _num(base.get("csat_gap_ci_lower")), "csat_gap_ci_upper": _num(base.get("csat_gap_ci_upper")),
            "handle_time_gap_ci_lower": _num(base.get("handle_time_gap_ci_lower")), "handle_time_gap_ci_upper": _num(base.get("handle_time_gap_ci_upper")),
            "sla_gap_ci_lower": _num(base.get("sla_gap_ci_lower")), "sla_gap_ci_upper": _num(base.get("sla_gap_ci_upper")),
            "metric_directions": metric_directions, "evidence_strength": evidence, "uncertainty": uncertainty,
            "diagnostic_state": diagnostic_state,
            "evidence_counts": {m: int(base.get(s["count"]) or 0) for m, s in METRICS.items()},
            "stability": {"state": stability_state, "by_metric": stability, "stage3_flag": source_stability},
            "economic_context": {"label": "observed exposure associated with resolved-ticket population; not savings or agent-attributed cost",
                "operational_exposure_inr": _num(econ.get("operational_cost_exposure_inr")),
                "transfer_exposure_inr": _num(econ.get("internal_transfer_cost_exposure_inr")),
                "replacement_exposure_inr": _num(econ.get("replacement_exposure_inr")),
                "refund_exposure_inr": _num(econ.get("refund_exposure_inr")),
                "total_relevant_exposure_inr": _num(econ.get("total_relevant_exposure_inr")),
                "training_cost_inr": None, "training_budget_inr": float(config.get("training_budget_inr", 400000))},
            "ai_evidence_status": ai_evidence_status,
            "training_theme": (ai.get("training_topics") or [None])[0] if ai_evidence_status == "available" else None,
            "representative_ticket_ids": list(ai.get("representative_ticket_ids") or []) if ai_evidence_status == "available" else [],
            "roster_coverage": round(roster_coverage, 4), "raw_metric_ranks": raw_ranks,
            "raw_mean_csat": _num(metric_row.get("mean_csat")), "raw_handle_time_mean": _num(metric_row.get("handle_time_mean")),
            "raw_sla_breach_rate": _num(metric_row.get("sla_breach_rate")),
            "priority_reason": reasons,
            "explanation": {"agent_id": agent_id, "priority": band, "why": reasons,
                "primary_training_theme": (ai.get("training_topics") or [None])[0] if ai_evidence_status == "available" else None,
                "supporting_ticket_ids": list(ai.get("representative_ticket_ids") or []) if ai_evidence_status == "available" else [],
                "economic_context": "Observed population exposure is contextual only; it is not attributed savings.",
                "caution": "Performance differences are observational; Stage 3 approximate uncertainty intervals must be considered."},
            "limitations": limitations, "sample_size": int(base.get("ticket_count") or 0),
            "peer_agent_count": int(base.get("peer_agent_count") or 0)})
    _assign_raw_ranks(rows)
    _assign_priority_ranks(rows)
    return rows


def _favorable(metric, row):
    spec = METRICS[metric]
    gap = _num(row.get(spec["gap"]))
    if gap is None:
        return False
    lower, upper = _num(row.get(spec["lower"])), _num(row.get(spec["upper"]))
    return lower > 0 if metric == "csat" else upper < 0


def _primary_signal(directions, row):
    concerns = [m for m in METRICS if directions[m] == "concern"]
    if not concerns:
        return "no_confirmed_adverse_signal"
    return max(concerns, key=lambda m: _severity(m, row, {}))


def _secondary_signal(directions, row):
    concerns = [m for m in METRICS if directions[m] == "concern"]
    ordered = sorted(concerns, key=lambda m: (-_severity(m, row, {}), m))
    return ordered[1] if len(ordered) > 1 else None


def _reasons(directions, gates, evidence, stability, status):
    labels = {"csat": "CSAT", "handle_time": "handle time", "sla": "SLA breach rate"}
    concerns = [labels[m] for m in METRICS if directions[m] == "concern"]
    favorable = [labels[m] for m in METRICS if directions[m] == "favorable"]
    if status == "not_rankable":
        return "Not ranked: " + ", ".join(sorted(set(gates))) if gates else "Not ranked because evidence or peer context is insufficient."
    if not concerns:
        return ("No adjusted metric has an interval wholly in the adverse direction; point estimates alone do not establish underperformance. "
                f"Evidence strength is {evidence}; stability state is {stability}.")
    return (f"Adverse adjusted evidence on {', '.join(concerns)}; evidence strength {evidence}; "
            f"period state {stability}." + (f" Favorable signal on {', '.join(favorable)} is retained as a conflict." if favorable else ""))


def _assign_raw_ranks(rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[str(r.get("tier"))].append(r)
    for agents in grouped.values():
        for key, getter, reverse in (("csat_low_is_worse", lambda r: r.get("raw_mean_csat"), False),
                                     ("handle_time_high_is_worse", lambda r: r.get("raw_handle_time_mean"), True),
                                     ("sla_high_is_worse", lambda r: r.get("raw_sla_breach_rate"), True)):
            vals = sorted((r for r in agents if getter(r) is not None), key=lambda r: ((-1 if reverse else 1) * getter(r), r["agent_id"]))
            for i, row in enumerate(vals, 1): row["raw_metric_ranks"][key] = i


def _assign_priority_ranks(rows):
    groups = defaultdict(list)
    for r in rows:
        if r["priority_status"] == "training_candidate":
            groups[(str(r.get("tier")), r.get("comparison_group"))].append(r)
    for group in groups.values():
        group.sort(key=lambda r: (-r["priority_score"], r["agent_id"]))
        for rank, row in enumerate(group, 1): row["priority_rank"] = rank


def sensitivity_summary(rows, comparisons, agent_metrics, economics, ai_rows, ai_status, config):
    scenarios = {
        "default_uncertainty_gate": dict(config),
        "point_estimate_only_exploratory": {**config, "require_interval_excludes_zero": False},
        "minimum_evidence_20": {**config, "minimum_metric_observations": 20, "minimum_agent_tickets": 20},
        "strict_evidence_60": {**config, "minimum_metric_observations": 60, "minimum_agent_tickets": 60},
        "alternate_weights_csat_heavy": {**config, "metric_weights": {"csat": .6, "handle_time": .25, "sla": .15}},
        "alternate_weights_operational": {**config, "metric_weights": {"csat": .25, "handle_time": .4, "sla": .35}},
        "conservative_stability_penalty": {**config, "stability_factors": {"persistent": 1.0, "mixed": .5, "single_period": .35, "no_clear_adverse_period_signal": .35, "insufficient_history": .2}},
    }
    results = {}
    for name, scenario in scenarios.items():
        out = build_priority_rows(comparisons, agent_metrics, economics, ai_rows, ai_status, scenario)
        ordered = [r["agent_id"] for r in sorted((x for x in out if x["priority_status"] == "training_candidate"), key=lambda x: (x["priority_rank"] or 10**9, x["agent_id"]))]
        results[name] = {"training_candidate_count": len(ordered), "candidate_agent_ids": ordered,
                         "high_priority_count": sum(r["priority_band"] == "high" for r in out)}
    default_ids = set(results["default_uncertainty_gate"]["candidate_agent_ids"])
    results["point_estimate_only_exploratory"]["overlap_with_default"] = len(default_ids & set(results["point_estimate_only_exploratory"]["candidate_agent_ids"]))
    unavailable = build_priority_rows(comparisons, agent_metrics, economics, ai_rows, "unavailable", config)
    available = build_priority_rows(comparisons, agent_metrics, economics, ai_rows, "available", config)
    ai_invariance = all(a["priority_score"] == b["priority_score"] and a["priority_status"] == b["priority_status"]
                        for a, b in zip(unavailable, available))
    return {"scenarios": results, "ai_status_invariance_verified": ai_invariance,
        "default_candidate_set_robust": all(set(v["candidate_agent_ids"]) == default_ids for k, v in results.items() if k != "point_estimate_only_exploratory"),
        "interpretation": "Point-estimate-only results are exploratory and cannot qualify candidates under the default uncertainty gate. Economic values and AI evidence do not change the deterministic score."}
