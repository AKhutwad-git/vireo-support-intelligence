"""Stage 3 comparison orchestration and report assembly (no ranking/decisions)."""
from __future__ import annotations
import json
from collections import Counter, defaultdict
from typing import Any
from .adjustment import adjusted_agent_metrics
from .case_mix import add_product_family, case_mix_metrics
from .peer_groups import build_peer_groups, attach_peer_groups, assignment_key
from .stability import assess_adjusted_stability

def _summary_rows(rows):
    return [{"comparison_group":group,"selected_assignment_count":len(items),"agent_count":max(r.get("peer_agent_count",0) for r in items),
             "fallback_level":items[0]["peer_fallback_level"],"tiers":sorted({str(r.get("agent_tier")) for r in items}),
             "teams":sorted({str(r.get("agent_team")) for r in items})}
            for group,items in _by(rows,"comparison_group").items() if group]

def _by(rows,key):
    d=defaultdict(list)
    for r in rows:d[r.get(key)].append(r)
    return d

def run_peer_analysis(tickets: list[dict[str,Any]], roster: list[dict[str,Any]], products: list[dict[str,Any]], config: dict[str,Any]) -> dict[str,Any]:
    min_agents=int(config.get("stage3",{}).get("min_peer_agents",3))
    min_cell=int(config.get("stage3",{}).get("min_peer_cell_observations",5))
    assignments=build_peer_groups(roster,min_agents=min_agents)
    enriched=add_product_family(tickets,products)
    enriched=attach_peer_groups(enriched,assignments)
    mix=case_mix_metrics(enriched)
    adjusted=adjusted_agent_metrics(enriched,min_cell_observations=min_cell)
    stability=assess_adjusted_stability(adjusted)
    stability_map={tuple(r.get(k) for k in ("agent_id","agent_team","agent_tier","agent_site","agent_shift","agent_from_date","agent_to_date"))+(r["outcome"],):r["stability_flag"] for r in stability}
    mix_map=defaultdict(dict)
    for row in mix:
        if row["period_type"]=="full_available_period":
            mix_map[assignment_key(row)].setdefault(row["dimension"],{})[row["level"]]=round(row["share"],6)
    comparisons=[]
    for row in adjusted:
        if row["period_type"]!="full_available_period":continue
        key=assignment_key(row)
        copy=dict(row)
        copy["case_mix_summary"]=json.dumps(mix_map.get(key,{}),sort_keys=True,ensure_ascii=False)
        flags={outcome:stability_map.get(key+(outcome,),"insufficient_period_evidence") for outcome in ("csat","handle_time","sla")}
        copy.update(csat_stability_flag=flags["csat"],handle_time_stability_flag=flags["handle_time"],sla_stability_flag=flags["sla"])
        copy["stability_flag"]="variable_across_quarters" if "variable_across_quarters" in flags.values() else ("no_clear_shift_detected" if all(v=="no_clear_shift_detected" for v in flags.values()) else "insufficient_period_evidence")
        copy["comparison_status"]="comparable" if copy.get("peer_supported") and any(copy.get(f"{o}_adjustment_coverage_count",0)>0 for o in ("csat","handle_time","sla")) else ("no_effective_assignment" if copy.get("peer_fallback_level")=="unmatched_context" else "insufficient_peer_support")
        comparisons.append(copy)
    # Detailed mix difference ranges are descriptive only, across assignment groups.
    mix_ranges={}
    for dimension in ("channel","priority","category","product_family"):
        values=defaultdict(list)
        for r in mix:
            if r["period_type"]=="full_available_period" and r["dimension"]==dimension and r.get("agent_tier") is not None and r["dimension_denominator"]>=30:
                values[r["level"]].append(r["share"])
        mix_ranges[dimension]={level:{"minimum_agent_share":min(shares),"maximum_agent_share":max(shares)} for level,shares in values.items()}
    comparable=[r for r in comparisons if r.get("comparison_status")=="comparable"]
    by_outcome={}
    adjustment_coverage={}
    for outcome,gapfield in (("csat","csat_gap"),("handle_time","handle_time_gap"),("sla","sla_gap")):
        vals=[r[gapfield] for r in comparisons if r.get(gapfield) is not None]
        by_outcome[outcome]={"adjusted_comparison_count":len(vals),"positive_gap_count":sum(v>0 for v in vals),"negative_gap_count":sum(v<0 for v in vals),
            "zero_gap_count":sum(v==0 for v in vals),"median_absolute_gap":_median([abs(v) for v in vals]),
            "gap_interval_direction_counts":dict(Counter(r.get(f"{outcome}_gap_interval_direction") for r in comparisons if r.get(gapfield) is not None))}
        covered=[r.get(f"{outcome}_adjustment_coverage_rate") for r in comparable if r.get(f"{outcome}_adjustment_coverage_rate") is not None]
        adjustment_coverage[outcome]={"assignments_with_any_coverage":sum(r.get(f"{outcome}_adjustment_coverage_count",0)>0 for r in comparable),
            "zero_coverage_assignment_count":sum(r.get(f"{outcome}_adjustment_coverage_count",0)==0 for r in comparable),
            "mean_coverage_rate":sum(covered)/len(covered) if covered else None,
            "minimum_coverage_rate":min(covered) if covered else None}
    unsupported=sum(not r.get("peer_supported") for r in assignments)
    low_evidence={o:sum(1 for r in comparable if r.get(f"{o}_eligible_count",0)<30) for o in ("csat","handle_time","sla")}
    period_low_evidence={o:sum(1 for r in adjusted if r.get("period_type")!="full_available_period" and r.get("comparison_group") and r.get(f"{o}_eligible_count",0)<30) for o in ("csat","handle_time","sla")}
    low_evidence_agents={o:sorted({r["agent_id"] for r in comparable if r.get(f"{o}_eligible_count",0)<30 and r.get("agent_id")}) for o in ("csat","handle_time","sla")}
    low_any_period={o:sorted({r["agent_id"] for r in adjusted if r.get("period_type")!="full_available_period" and r.get("comparison_group") and r.get(f"{o}_eligible_count",0)<30 and r.get("agent_id")}) for o in ("csat","handle_time","sla")}
    fallback_counts={o:dict(Counter(r.get(f"{o}_fallback_level") for r in comparable)) for o in ("csat","handle_time","sla")}
    report={"status":"PASS","peer_group_count":len({r["comparison_group"] for r in assignments if r.get("comparison_group")}),
        "peer_groups":_summary_rows(assignments),"minimum_peer_agents":min_agents,"minimum_peer_cell_observations":min_cell,
        "assignment_context_count":len(assignments),"unsupported_peer_assignment_count":unsupported,
        "comparison_assignment_count":sum(r["comparison_status"]=="comparable" for r in comparisons),
        "comparison_rows":len(comparisons),"unmatched_assignment_context_rows":sum(r["comparison_status"]=="no_effective_assignment" for r in comparisons),
        "insufficient_peer_comparison_rows":sum(r["comparison_status"]=="insufficient_peer_support" for r in comparisons),
        "ticket_rows_preserved":len(tickets),"case_mix_share_ranges":mix_ranges,
        "raw_adjusted_gap_summary":by_outcome,"adjustment_coverage_by_outcome":adjustment_coverage,"low_evidence_assignment_count_by_outcome":low_evidence,
        "low_evidence_period_count_by_outcome":period_low_evidence,"low_evidence_agent_ids_full_period":low_evidence_agents,
        "low_evidence_agent_ids_in_any_month_or_quarter":low_any_period,"adjustment_fallback_counts":fallback_counts,
        "stability_flag_counts":dict(Counter(r["stability_flag"] for r in stability)),"stability_rows":len(stability),
        "open_pending_csat_anomaly_count":sum(bool(r.get("csat_unexpected_status_flag")) for r in tickets),
        "adjustment_method":"Leave-one-agent-out, peer-group-standardized differences in outcome means. Each focal ticket receives a peer outcome mean for a hierarchical work-mix cell; fallback proceeds from channel × priority × quarter × product family to broader cells and finally same peer group. Tier never crosses.",
        "uncertainty_method":"Approximate 95% normal intervals; agent sample variance plus peer-cell mean variance. Ticket independence assumed; intervals are descriptive and do not account for clustering or model-selection uncertainty.",
        "limitations":["Observational adjusted gaps do not establish causation.","Category excluded from adjustment because intake category may be retagged by agents at closure.","Transfers, resolution behavior, handle time, SLA, refunds, and replacements are post-routing/outcome variables and are excluded from case-mix adjustment.","Stage 2 agent_id identifies the resolver, not necessarily the first responder; SLA comparisons are resolver-associated ticket outcomes.","Assignment contexts without effective roster data are retained in output with no-comparison status.","Case-mix model uses channel, priority, quarter, product family, and tier-safe team/peer grouping; site and shift are peer-group fallback dimensions.","Small outcome samples have wide or undefined intervals; a <30 label is descriptive, not a decision threshold.","Confidence intervals assume independent tickets and understate uncertainty when tickets cluster by agent, peer cell, or period."]}
    return {"peer_groups":assignments,"case_mix_metrics":mix,"adjusted_agent_metrics":adjusted,"agent_comparison":comparisons,
            "stability_metrics":stability,"report":report,"enriched_tickets":enriched}

def _median(values):
    if not values:return None
    values=sorted(values); n=len(values)
    return values[n//2] if n%2 else (values[n//2-1]+values[n//2])/2
