from vireo.scoring.priority import build_priority_rows


def fixture_rows(count=1):
    agents=[]; comparisons=[]; economics=[]
    for i in range(count):
        aid=f"A{i+1}"
        agents.append({"agent_id":aid,"ticket_count":100,"completed_ticket_count":90})
        economics.append({"agent_id":aid,"operational_cost_exposure_inr":1000,"total_relevant_exposure_inr":2500})
        full={"agent_id":aid,"agent_team":"Chat Frontline","agent_tier":"1","ticket_count":100,"comparison_group":"tier=1|team=Chat Frontline",
            "peer_supported":True,"peer_agent_count":4,"comparison_status":"comparable","stability_flag":"no_clear_shift_detected",
            "csat_gap":-.8,"csat_gap_ci_lower":-1.2,"csat_gap_ci_upper":-.4,"csat_gap_interval_direction":"below_zero",
            "csat_eligible_count":50,"csat_adjustment_coverage_rate":1.,
            "handle_time_gap":50.,"peer_handle_time_mean":100.,"handle_time_gap_ci_lower":10.,"handle_time_gap_ci_upper":90.,"handle_time_gap_interval_direction":"above_zero",
            "handle_time_eligible_count":80,"handle_time_adjustment_coverage_rate":1.,
            "sla_gap":.1,"sla_gap_ci_lower":.03,"sla_gap_ci_upper":.17,"sla_gap_interval_direction":"above_zero",
            "sla_eligible_count":100,"sla_adjustment_coverage_rate":1.}
        comparisons.append(full)
        for quarter in ("2025-Q1","2025-Q2"):
            comparisons.append({**full,"period_type":"quarter","period":quarter,"csat_gap_ci_lower":-.8,"csat_gap_ci_upper":-.1,
                "handle_time_gap_ci_lower":5.,"handle_time_gap_ci_upper":70.,"sla_gap_ci_lower":.01,"sla_gap_ci_upper":.1})
        full["period_type"]="full_available_period"
    return comparisons,agents,economics


def test_builds_explained_priority_and_tier_safe_rank():
    comp,agents,econ=fixture_rows(2)
    out=build_priority_rows(comp,agents,econ,[],"unavailable",{"minimum_agent_tickets":30,"minimum_metric_observations":30})
    assert len(out)==2
    assert all(r["priority_status"]=="training_candidate" and r["priority_band"]=="high" for r in out)
    assert all(r["review_score_status"] == "descriptive_peer_adjusted_review_only" for r in out)
    assert {r["priority_rank"] for r in out}=={1,2}
    assert all(r["ai_evidence_status"]=="unavailable" and not r["representative_ticket_ids"] for r in out)
    assert "not causal" in out[0]["priority_reason"] or "Adverse adjusted" in out[0]["priority_reason"]


def test_tiers_do_not_share_priority_rank_space():
    comp,agents,econ=fixture_rows(2)
    second=next(r for r in comp if r["agent_id"]=="A2" and r["period_type"]=="full_available_period")
    second["agent_tier"]="2"
    second["comparison_group"]="tier=2|team=Warranty"
    for r in comp:
        if r["agent_id"]=="A2":
            r["agent_tier"]="2"; r["comparison_group"]="tier=2|team=Warranty"
    out=build_priority_rows(comp,agents,econ,[],"unavailable",{})
    assert [r["priority_rank"] for r in out]==[1,1]
