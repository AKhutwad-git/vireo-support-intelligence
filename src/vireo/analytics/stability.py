"""Time-period outcome summaries and uncertainty-overlap stability flags."""
from __future__ import annotations
from collections import defaultdict
from typing import Any
from .peer_groups import ASSIGNMENT_FIELDS
from .uncertainty import mean_interval

OUTCOMES={"csat":("valid_for_csat","csat_score_numeric",(1,5)),"handle_time":("valid_for_handle_time","handle_time_minutes",None),"sla":("valid_for_sla","sla_breach_flag",(0,1))}

def period_outcomes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped=defaultdict(list)
    for r in rows:
        for period_type,field in (("month","reporting_month"),("quarter","reporting_quarter")):
            if r.get(field): grouped[(tuple(r.get(k) for k in ASSIGNMENT_FIELDS),period_type,r[field])].append(r)
    output=[]
    for (assignment,period_type,period),group in grouped.items():
        base=dict(zip(ASSIGNMENT_FIELDS,assignment))
        for outcome,(eligible,field,bounds) in OUTCOMES.items():
            vals=[float(r[field]) for r in group if r.get(eligible) and r.get(field) is not None]
            stats=mean_interval(vals,bounds=bounds)
            output.append({**base,"period_type":period_type,"period":period,"outcome":outcome,
                           "eligible_count":len(vals),"mean":stats["mean"],"standard_error":stats["standard_error"],
                           "ci_lower":stats["ci_lower"],"ci_upper":stats["ci_upper"]})
    return output

def assess_stability(period_rows: list[dict[str, Any]], min_periods: int=2) -> list[dict[str, Any]]:
    groups=defaultdict(list)
    for r in period_rows:
        if r.get("period_type")=="quarter" and r.get("eligible_count",0)>=2 and r.get("ci_lower") is not None:
            key=tuple(r.get(k) for k in ASSIGNMENT_FIELDS)+(r.get("outcome"),)
            groups[key].append(r)
    output=[]
    for key,periods in groups.items():
        periods=sorted(periods,key=lambda x:x["period"])
        if len(periods)<min_periods: flag="insufficient_period_evidence"
        else:
            overlap=all(max(a["ci_lower"],b["ci_lower"])<=min(a["ci_upper"],b["ci_upper"]) for i,a in enumerate(periods) for b in periods[i+1:])
            flag="no_clear_shift_detected" if overlap else "variable_across_quarters"
        output.append({**dict(zip(ASSIGNMENT_FIELDS,key[:len(ASSIGNMENT_FIELDS)])),"outcome":key[-1],
                       "qualifying_quarter_count":len(periods),"stability_flag":flag,
                       "quarterly_range":(max(p["mean"] for p in periods)-min(p["mean"] for p in periods)) if periods else None})
    return output

def assess_adjusted_stability(adjusted_rows: list[dict[str, Any]], min_periods: int=2) -> list[dict[str, Any]]:
    """Stability of case-mix-adjusted quarterly gaps, avoiding raw-mix confounding."""
    normalized=[]
    for row in adjusted_rows:
        if row.get("period_type")!="quarter" or not row.get("comparison_group"):
            continue
        for outcome in OUTCOMES:
            if not row.get(f"{outcome}_adjustment_coverage_count"):
                continue
            normalized.append({**{k:row.get(k) for k in ASSIGNMENT_FIELDS},"period_type":"quarter","period":row["period"],"outcome":outcome,
                "eligible_count":row.get(f"{outcome}_adjustment_coverage_count",0),"mean":row.get({"csat":"csat_gap","handle_time":"handle_time_gap","sla":"sla_gap"}[outcome]),
                "ci_lower":row.get(f"{outcome}_gap_ci_lower"),"ci_upper":row.get(f"{outcome}_gap_ci_upper")})
    return assess_stability(normalized,min_periods)
