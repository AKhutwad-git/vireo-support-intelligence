"""Independent checks of synthetic decision behavior and explanation consistency."""
from __future__ import annotations


def explanation_consistency(decisions):
    checks = []
    labels = {"csat": "CSAT", "handle_time": "handle time", "sla": "SLA"}
    for row in decisions:
        text = str(row.get("priority_reason", "")).casefold()
        directions = row.get("metric_directions") or {}
        concern_clause = text.split(" favorable signal", 1)[0]
        for metric, label in labels.items():
            stated = label.casefold() in concern_clause and "adverse adjusted evidence" in concern_clause
            expected = directions.get(metric) == "concern"
            checks.append({"agent_id": row.get("agent_id"), "rule": f"{metric}_concern_explanation_matches",
                "status": "PASS" if stated == expected else "FAIL"})
        unavailable = row.get("ai_evidence_status") in ("unavailable", "failed")
        ai_claim = bool(row.get("training_theme") or row.get("representative_ticket_ids") or
                        (row.get("explanation") or {}).get("primary_training_theme"))
        checks.append({"agent_id": row.get("agent_id"), "rule": "no_ai_claim_when_unavailable",
            "status": "FAIL" if unavailable and ai_claim else "PASS"})
        insufficient = "insufficient_evidence" in (row.get("eligibility_gates") or [])
        high = row.get("priority_band") == "high"
        checks.append({"agent_id": row.get("agent_id"), "rule": "insufficient_evidence_not_high",
            "status": "FAIL" if insufficient and high else "PASS"})
    return checks
