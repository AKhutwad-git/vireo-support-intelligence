"""Descriptive work-mix distributions by effective agent assignment."""
from __future__ import annotations
from collections import Counter, defaultdict
from typing import Any
from .peer_groups import ASSIGNMENT_FIELDS

DIMENSIONS=("channel","priority","category","product_family","agent_team","agent_tier","agent_site","agent_shift","reporting_month","reporting_quarter")

def add_product_family(rows: list[dict[str, Any]], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family={p.get("sku"):p.get("family") for p in products}
    return [{**r,"product_family":family.get(r.get("product_sku"))} for r in rows]

def case_mix_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output=[]
    contexts=defaultdict(list)
    for r in rows:
        contexts[tuple(r.get(f) for f in ASSIGNMENT_FIELDS)].append(r)
    for context, group in contexts.items():
        assignment=dict(zip(ASSIGNMENT_FIELDS,context))
        periods=[("full_available_period","all",group)]
        periods.extend(("quarter",p,[r for r in group if r.get("reporting_quarter")==p]) for p in sorted({r.get("reporting_quarter") for r in group if r.get("reporting_quarter")}))
        for period_type,period,subset in periods:
            for dimension in DIMENSIONS:
                counts=Counter(str(r.get(dimension)) if r.get(dimension) not in (None,"") else "(missing)" for r in subset)
                n=len(subset)
                for level,count in sorted(counts.items()):
                    output.append({**assignment,"period_type":period_type,"period":period,"dimension":dimension,"level":level,
                                   "ticket_count":count,"dimension_denominator":n,"share":count/n if n else None,
                                   "missing_level_flag":level=="(missing)"})
    return output
