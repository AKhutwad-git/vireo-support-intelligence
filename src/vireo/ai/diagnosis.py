"""Evidence-preserving fields for diagnostics; model output remains ticket-grounded."""

def to_ticket_row(candidate, result, model, prompt_version, status="analyzed"):
    return {"ticket_id": candidate["ticket_id"], "agent_id": candidate.get("agent_id"),
        "status": candidate.get("status"), "attendance_flag": bool(candidate.get("attendance_flag")),
        "team": candidate.get("agent_team"), "tier": candidate.get("agent_tier"),
        "site": candidate.get("agent_site"), "shift": candidate.get("agent_shift"),
        "agent_from_date": candidate.get("agent_from_date"), "agent_to_date": candidate.get("agent_to_date"),
        "agent_assignment_flag": candidate.get("agent_assignment_flag"),
        "comparison_group": candidate.get("comparison_group"), "peer_supported": bool(candidate.get("peer_supported")),
        "model": model, "prompt_version": prompt_version,
        "issue_category": result.get("issue_category"), "secondary_category": result.get("secondary_category"),
        "customer_intent": result.get("customer_intent"), "diagnostic_theme": result.get("diagnostic_theme"),
        "customer_problem": result.get("customer_problem"), "resolution_pattern": result.get("resolution_pattern"),
        "communication_issue": result.get("communication_issue"), "policy_process_issue": result.get("policy_process_issue"),
        "possible_failure_theme": result.get("possible_failure_theme"), "evidence": result.get("evidence"),
        "confidence": result.get("confidence"), "evidence_strength": result.get("evidence_strength"),
        "text_quality_state": candidate.get("text_quality_state"), "selection_signals": candidate.get("selection_signals", []),
        "analysis_status": status}
