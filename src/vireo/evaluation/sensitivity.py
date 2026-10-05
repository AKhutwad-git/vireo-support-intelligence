"""Stage 6 parameter sensitivity without changing the configured default."""
from __future__ import annotations

from vireo.scoring.priority import build_priority_rows


def _jaccard(a, b):
    union = set(a) | set(b)
    return len(set(a) & set(b)) / len(union) if union else 1.0


def _rank_correlation(left, right):
    keys = sorted(set(left) & set(right))
    if len(keys) < 2:
        return None
    def rank(values):
        ordered = sorted(enumerate(values), key=lambda p: (p[1], p[0]))
        result = [0.0] * len(values)
        i = 0
        while i < len(ordered):
            j = i + 1
            while j < len(ordered) and ordered[j][1] == ordered[i][1]:
                j += 1
            avg_rank = ((i + 1) + j) / 2
            for k in range(i, j):
                result[ordered[k][0]] = avg_rank
            i = j
        return result
    x = rank([left[k] for k in keys])
    y = rank([right[k] for k in keys])
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    mx, my = sum(x)/len(x), sum(y)/len(y)
    cov = sum((a-mx)*(b-my) for a,b in zip(x,y))
    vx = sum((a-mx)**2 for a in x) ** .5
    vy = sum((b-my)**2 for b in y) ** .5
    return cov/(vx*vy) if vx and vy else None


def evaluate_sensitivity(comparisons, agents, economics, ai, ai_status, config):
    scenarios = {
        "default": dict(config),
        "alternate_weights_csat_heavy": {**config, "metric_weights": {"csat": .6, "handle_time": .25, "sla": .15}},
        "alternate_weights_operational": {**config, "metric_weights": {"csat": .25, "handle_time": .4, "sla": .35}},
        "gap_scales_narrower": {**config, "csat_gap_scale": .4, "handle_time_relative_gap_scale": .20, "sla_gap_scale": .04},
        "gap_scales_wider": {**config, "csat_gap_scale": .7, "handle_time_relative_gap_scale": .35, "sla_gap_scale": .07},
        "minimum_evidence_20": {**config, "minimum_metric_observations": 20, "minimum_agent_tickets": 20},
        "minimum_evidence_60": {**config, "minimum_metric_observations": 60, "minimum_agent_tickets": 60},
        "point_estimate_only_exploratory": {**config, "require_interval_excludes_zero": False},
        "conservative_stability": {**config, "stability_factors": {"persistent":1.,"mixed":.5,"single_period":.35,"no_clear_adverse_period_signal":.35,"insufficient_history":.2}},
    }
    decisions = {}
    records = []
    for name, parameters in scenarios.items():
        rows = build_priority_rows(comparisons, agents, economics, ai, ai_status, parameters)
        candidates = sorted((r for r in rows if r["priority_status"] == "training_candidate"),
                            key=lambda r: (r["priority_rank"] or 10**9, r["agent_id"]))
        ids = [r["agent_id"] for r in candidates]
        decisions[name] = {"rows": rows, "ids": ids}
    default_rows = decisions["default"]["rows"]
    default_by_id = {r["agent_id"]:r for r in default_rows}
    default_bands = {k:v["priority_band"] for k,v in default_by_id.items()}
    default_scores = {k:v["priority_score"] for k,v in default_by_id.items()}
    for name, decision in decisions.items():
        rows = decision["rows"]
        by_id = {r["agent_id"]:r for r in rows}
        changed = sum(by_id[k]["priority_band"] != default_bands[k] for k in default_bands)
        records.append({"scenario":name,"candidate_count":len(decision["ids"]),"candidate_agent_ids":decision["ids"],
            "candidate_set_jaccard_vs_default":_jaccard(decision["ids"], decisions["default"]["ids"]),
            "priority_band_changes_vs_default":changed,
            "priority_score_rank_correlation_vs_default":_rank_correlation(default_scores,{k:v["priority_score"] for k,v in by_id.items()}),
            "configuration":{k:v for k,v in scenarios[name].items() if k in ("metric_weights","require_interval_excludes_zero","minimum_metric_observations","minimum_agent_tickets","csat_gap_scale","handle_time_relative_gap_scale","sla_gap_scale")}})
    sets = [set(v["ids"]) for k,v in decisions.items() if k != "point_estimate_only_exploratory"]
    robust = set.intersection(*sets) if sets else set()
    union = set.union(*sets) if sets else set()
    summary = {"scenarios":{r["scenario"]:{"candidate_count":r["candidate_count"],"candidate_agent_ids":r["candidate_agent_ids"],
                    "candidate_set_jaccard_vs_default":r["candidate_set_jaccard_vs_default"],
                    "priority_band_changes_vs_default":r["priority_band_changes_vs_default"],
                    "priority_score_rank_correlation_vs_default":r["priority_score_rank_correlation_vs_default"]} for r in records},
        "robust_candidates":sorted(robust),"assumption_sensitive_candidates":sorted(union-robust),
        "point_estimate_only_candidates":decisions["point_estimate_only_exploratory"]["ids"],
        "priority_rank_correlation_unavailable_when_candidate_sets_empty":True}
    return summary, records
