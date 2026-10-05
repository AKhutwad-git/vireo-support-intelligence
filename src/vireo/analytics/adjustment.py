"""Leave-one-agent-out direct standardization against comparable peer work."""
from __future__ import annotations
from collections import Counter, defaultdict
from statistics import mean, stdev
from math import sqrt
from typing import Any
from .peer_groups import ASSIGNMENT_FIELDS, assignment_key
from .uncertainty import mean_interval, standardized_gap_interval, evidence_label

OUTCOMES={
    "csat": {"eligible":"valid_for_csat","value":"csat_score_numeric","raw":"raw_mean_csat","peer":"peer_mean_csat","gap":"csat_gap","bounds":(1,5)},
    "handle_time": {"eligible":"valid_for_handle_time","value":"handle_time_minutes","raw":"raw_handle_time_mean","peer":"peer_handle_time_mean","gap":"handle_time_gap","bounds":None},
    "sla": {"eligible":"valid_for_sla","value":"sla_breach_flag","raw":"raw_sla_breach_rate","peer":"peer_sla_breach_rate","gap":"sla_gap","bounds":(0,1)},
}
STRATA=(
    ("channel_priority_period_product",("channel","priority","reporting_quarter","product_family")),
    ("channel_priority_period",("channel","priority","reporting_quarter")),
    ("channel_priority",("channel","priority")),
    ("channel",("channel",)),
    ("peer_group_only",()),
)
DEFAULT_MIN_PEER_CELL_OBSERVATIONS=5

def _norm(value): return value if value not in (None,"") else "(missing)"

def _period_slices(rows):
    out=[("full_available_period","all",rows)]
    for field,kind in (("reporting_quarter","quarter"),("reporting_month","month")):
        for val in sorted({r.get(field) for r in rows if r.get(field)}):
            out.append((kind,val,[r for r in rows if r.get(field)==val]))
    return out

def _outcome_value(row, spec):
    value=row.get(spec["value"])
    return float(value) if value is not None else None

def _pool_keys(row):
    tier=row.get("agent_tier"); team=row.get("agent_team"); site=row.get("agent_site"); shift=row.get("agent_shift")
    return (_label(tier,team,site,shift),_label(tier,team),_label(tier,None))

def _label(tier,team,site=None,shift=None):
    parts=[("tier",tier)]
    if team is not None:parts.append(("team",team))
    if site is not None:parts.append(("site",site))
    if shift is not None:parts.append(("shift",shift))
    return "|".join(f"{k}={v}" for k,v in parts)

def _estimate(focus, peers, outcome, spec, min_cell_observations):
    eligible=spec["eligible"]
    observed=[float(_outcome_value(r,spec)) for r in focus if r.get(eligible) and _outcome_value(r,spec) is not None]
    focal_ids={r.get("agent_id") for r in focus}
    peer_rows=[r for r in peers if r.get(eligible) and _outcome_value(r,spec) is not None and r.get("agent_id") not in focal_ids]
    peer_values=[float(_outcome_value(r,spec)) for r in peer_rows]
    peer_ids={r.get("agent_id") for r in peer_rows}
    indexes=[]
    for label,features in STRATA:
        index=defaultdict(list)
        for r in peer_rows:
            index[tuple(_norm(r.get(f)) for f in features)].append(r)
        indexes.append((label,features,index))
    expected=[]; chosen_cells=[]; matched_observed=[]; fallback=Counter()
    for ticket in focus:
        val=_outcome_value(ticket,spec)
        if not ticket.get(eligible) or val is None: continue
        matched=None; used="unsupported"
        for label,features,index in indexes:
            candidates=index.get(tuple(_norm(ticket.get(f)) for f in features),[])
            ids={r.get("agent_id") for r in candidates}
            if len(candidates)>=min_cell_observations and len(ids)>=2:
                matched=[float(_outcome_value(r,spec)) for r in candidates]; used=label; break
        if matched is not None:
            expected.append(float(mean(matched))); chosen_cells.append(matched); matched_observed.append(float(val)); fallback[used]+=1
    coverage=len(expected); n=len(observed)
    raw_stats=mean_interval(observed,bounds=spec["bounds"])
    raw=raw_stats["mean"]
    peer_mean=sum(expected)/coverage if coverage else None
    ci=standardized_gap_interval(matched_observed,chosen_cells,len(peer_values),gap_bounds=(-4,4) if outcome=="csat" else ((-1,1) if outcome=="sla" else None)) if coverage else {"sample_size":0,"standard_error":None,"ci_lower":None,"ci_upper":None}
    # Approximate expected-mean SE conditional on focal mix.
    peer_se=sqrt(sum((stdev(c)**2/len(c) if len(c)>1 else 0) for c in chosen_cells))/(coverage) if coverage else None
    fallback_level=max(fallback,key=fallback.get) if fallback else "no_supported_peer_cell"
    prefix=outcome
    gap=(mean(matched_observed)-peer_mean) if coverage else None
    interval_direction="insufficient" if ci["ci_lower"] is None else ("higher" if ci["ci_lower"]>0 else ("lower" if ci["ci_upper"]<0 else "overlaps_zero"))
    return {spec["raw"]:raw,spec["peer"]:peer_mean,spec["gap"]:gap,
        f"{prefix}_eligible_count":n,f"{prefix}_peer_sample_size":len(peer_values),f"{prefix}_distinct_peer_count":len(peer_ids),
        f"{prefix}_adjustment_coverage_count":coverage,f"{prefix}_adjustment_coverage_rate":coverage/n if n else None,
        f"{prefix}_standard_error":raw_stats["standard_error"],f"{prefix}_raw_ci_lower":raw_stats["ci_lower"],f"{prefix}_raw_ci_upper":raw_stats["ci_upper"],
        f"{prefix}_gap_standard_error":ci["standard_error"],f"{prefix}_gap_ci_lower":ci["ci_lower"],f"{prefix}_gap_ci_upper":ci["ci_upper"],
        f"{prefix}_gap_interval_direction":interval_direction,
        f"{prefix}_peer_mean_standard_error":peer_se,f"{prefix}_fallback_level":fallback_level,
        f"{prefix}_evidence_strength":evidence_label(n)}

def adjusted_agent_metrics(rows: list[dict[str,Any]], min_cell_observations: int=DEFAULT_MIN_PEER_CELL_OBSERVATIONS) -> list[dict[str,Any]]:
    by_assignment=defaultdict(list); by_group=defaultdict(list)
    for row in rows:
        by_assignment[assignment_key(row)].append(row)
        if row.get("comparison_group") and row.get("peer_supported"):
            for pool in _pool_keys(row): by_group[pool].append(row)
    output=[]
    for akey, history in by_assignment.items():
        agent=history[0]
        for period_type,period,focus in _period_slices(history):
            peers_all=by_group.get(agent.get("comparison_group"),[]) if agent.get("comparison_group") else []
            if period_type=="quarter": peers=[r for r in peers_all if r.get("reporting_quarter")==period]
            elif period_type=="month": peers=[r for r in peers_all if r.get("reporting_month")==period]
            else: peers=peers_all
            peers=[r for r in peers if r.get("agent_id")!=agent.get("agent_id")]
            record={**{k:agent.get(k) for k in ASSIGNMENT_FIELDS},"comparison_group":agent.get("comparison_group"),
                    "peer_fallback_level":agent.get("peer_fallback_level"),"peer_agent_count":agent.get("peer_agent_count"),
                    "peer_supported":bool(agent.get("peer_supported")),"period_type":period_type,"period":period,
                    "ticket_count":len(focus)}
            for name,spec in OUTCOMES.items():
                record.update(_estimate(focus,peers,name,spec,min_cell_observations))
            output.append(record)
    return sorted(output,key=lambda r:(str(r.get("agent_id")),str(r.get("agent_from_date")),r["period_type"],r["period"]))
