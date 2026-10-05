"""Deterministic evidence aggregation from validated ticket analyses only."""
from __future__ import annotations
from collections import defaultdict, Counter


TRAINING_TOPIC_MAP = {"product_knowledge": "product knowledge", "policy_knowledge": "policy knowledge",
    "resolution_workflow": "resolution workflow", "escalation_handling": "escalation handling",
    "communication_clarity": "communication clarity", "expectation_management": "expectation management",
    "troubleshooting": "troubleshooting"}


def aggregate_agent_diagnostics(ticket_rows, selected_agent_ids=None):
    groups = defaultdict(list)
    for row in ticket_rows:
        if row.get("analysis_status") == "analyzed" and row.get("agent_id") and row.get("attendance_flag"):
            groups[row["agent_id"]].append(row)
    if selected_agent_ids is not None:
        for agent in selected_agent_ids: groups.setdefault(agent, [])
    output = []
    for agent, rows in sorted(groups.items()):
        themes = Counter(r.get("issue_category") for r in rows if r.get("issue_category") not in (None,"unclear","insufficient_evidence"))
        patterns = Counter(r.get("diagnostic_theme") for r in rows if r.get("diagnostic_theme") not in (None,"no_recurring_theme","unclear","insufficient_evidence"))
        dominant = sorted(themes.items(), key=lambda x: (-x[1], str(x[0])))[:3]
        recurrent = sorted(patterns.items(), key=lambda x: (-x[1], str(x[0])))
        topics = sorted({TRAINING_TOPIC_MAP[t] for t, count in recurrent if count >= 2 and t in TRAINING_TOPIC_MAP})
        representatives = [r["ticket_id"] for r in sorted(rows, key=lambda r: (-r.get("confidence", 0), r["ticket_id"]))[:5]]
        strengths = [r.get("evidence_strength") for r in rows]
        overall = "high" if len(rows) >= 5 and strengths.count("high") >= 3 else "moderate" if len(rows) >= 3 else "low" if rows else "insufficient"
        output.append({"agent_id": agent, "sample_size": len(rows),
            "teams": sorted({r.get("team") for r in rows if r.get("team")}),"tiers": sorted({r.get("tier") for r in rows if r.get("tier")}),
            "model": rows[0].get("model"),"prompt_version": rows[0].get("prompt_version"),
            "dominant_issue_themes": [{"theme": t, "count": n} for t,n in dominant],
            "recurring_failure_patterns": [{"theme": t, "count": n} for t,n in recurrent if n >= 2],
            "themes": [{"theme": t, "count": n} for t,n in recurrent if n >= 2],
            "training_topics": topics, "representative_ticket_ids": representatives,
            "evidence_strength": overall, "overall_evidence_strength": overall,
            "limitations": ["Selected ticket sample; not a full-population review.", "Associations do not establish agent causality.", "Theme labels are model-generated and require human review."]})
    return output


def aggregate_peer_diagnostics(ticket_rows):
    groups=defaultdict(list)
    for row in ticket_rows:
        if row.get("analysis_status")=="analyzed" and row.get("attendance_flag") and row.get("peer_supported") and row.get("comparison_group"):
            groups[row["comparison_group"]].append(row)
    output=[]
    for peer,rows in sorted(groups.items()):
        themes=Counter(r.get("diagnostic_theme") for r in rows if r.get("diagnostic_theme") not in (None,"no_recurring_theme","unclear","insufficient_evidence"))
        issues=Counter(r.get("issue_category") for r in rows if r.get("issue_category") not in (None,"unclear","insufficient_evidence"))
        recurrent=sorted(themes.items(),key=lambda x:(-x[1],str(x[0])))
        topics=sorted({TRAINING_TOPIC_MAP[t] for t,n in recurrent if n>=2 and t in TRAINING_TOPIC_MAP})
        ids=[r["ticket_id"] for r in sorted(rows,key=lambda r:(-r.get("confidence",0),r["ticket_id"]))[:5]]
        strengths=[r.get("evidence_strength") for r in rows]
        strength="high" if len(rows)>=5 and strengths.count("high")>=3 else "moderate" if len(rows)>=3 else "low"
        output.append({"peer_group_id":peer,"sample_size":len(rows),"dominant_issue_themes":[{"theme":t,"count":n} for t,n in sorted(issues.items(),key=lambda x:(-x[1],str(x[0])))[:3]],
            "model":rows[0].get("model"),"prompt_version":rows[0].get("prompt_version"),
            "recurring_patterns":[{"theme":t,"count":n} for t,n in recurrent if n>=2],"training_topics":topics,
            "representative_ticket_ids":ids,"evidence_strength":strength,
            "limitations":["Selected ticket sample; not a full peer-group census.","Peer association does not establish cause.","Theme labels require human review."]})
    return output
