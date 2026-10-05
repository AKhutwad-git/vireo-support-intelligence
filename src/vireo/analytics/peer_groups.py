"""Tier-safe, assignment-aware peer-group construction with documented fallbacks."""
from __future__ import annotations
from collections import defaultdict
from typing import Any

ASSIGNMENT_FIELDS = ("agent_id", "agent_team", "agent_tier", "agent_site", "agent_shift", "agent_from_date", "agent_to_date")

def assignment_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row.get("agent_id"), row.get("agent_team") or None, row.get("agent_tier") or None,
            row.get("agent_site") or None, row.get("agent_shift") or None,
            row.get("agent_from_date") or None, row.get("agent_to_date") or None)

def _label(tier, team, site=None, shift=None):
    parts = [("tier",tier)]
    if team is not None: parts.append(("team",team))
    if site is not None: parts.append(("site",site))
    if shift is not None: parts.append(("shift",shift))
    return "|".join(f"{k}={v}" for k,v in parts)

def build_peer_groups(roster: list[dict[str, Any]], min_agents: int = 3) -> list[dict[str, Any]]:
    """Group by tier/team/site/shift where supported, fall back to tier/team then tier.

    Tier is always part of the key. `min_agents=3` means at least two distinct peers
    remain after leave-one-agent-out estimation; smaller tiers are marked unsupported.
    """
    assignments = []
    for r in roster:
        assignments.append({"agent_id":r.get("agent_id"), "agent_team":r.get("team"), "agent_tier":r.get("tier"),
            "agent_site":r.get("site"), "agent_shift":r.get("shift"), "agent_from_date":r.get("from_date"), "agent_to_date":r.get("to_date") or None})
    member_sets = {}
    for fields in (("agent_tier","agent_team","agent_site","agent_shift"),("agent_tier","agent_team"),("agent_tier",)):
        grouped=defaultdict(set)
        for a in assignments:
            k=tuple(a.get(f) for f in fields)
            grouped[k].add(a.get("agent_id"))
        member_sets[fields]=grouped
    output=[]
    for a in assignments:
        options=(("tier_team_site_shift",("agent_tier","agent_team","agent_site","agent_shift")),
                 ("tier_team",("agent_tier","agent_team")),("tier_only",("agent_tier",)))
        selected=None; level="insufficient_peers"; count=0
        for label,fields in options:
            k=tuple(a.get(f) for f in fields)
            n=len(member_sets[fields][k])
            if n>=min_agents:
                selected=(label,fields,k); level=label; count=n; break
        group_id=None
        if selected:
            _,fields,k=selected
            if fields==("agent_tier",): group_id=_label(a.get("agent_tier"),None)
            elif fields==("agent_tier","agent_team"): group_id=_label(a.get("agent_tier"),a.get("agent_team"))
            else: group_id=_label(a.get("agent_tier"),a.get("agent_team"),a.get("agent_site"),a.get("agent_shift"))
        output.append({**a,"comparison_group":group_id,"peer_fallback_level":level,"peer_agent_count":count,
                       "peer_supported":group_id is not None,"minimum_peer_agents":min_agents})
    return output

def attach_peer_groups(rows: list[dict[str, Any]], peer_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup={assignment_key(r):r for r in peer_groups}
    out=[]
    for row in rows:
        group=lookup.get(assignment_key(row)) if row.get("agent_assignment_flag")=="matched" else None
        out.append({**row,"comparison_group":group.get("comparison_group") if group else None,
                    "peer_fallback_level":group.get("peer_fallback_level") if group else "unmatched_context",
                    "peer_agent_count":group.get("peer_agent_count",0) if group else 0,"peer_supported":bool(group and group.get("peer_supported"))})
    return out
