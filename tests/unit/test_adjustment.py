from vireo.analytics.adjustment import adjusted_agent_metrics

def row(agent,score,team="Frontline",tier="1"):
    return {"agent_id":agent,"agent_team":team,"agent_tier":tier,"agent_site":"Pune","agent_shift":"Day","agent_from_date":"2025-01-01","agent_to_date":"",
        "agent_assignment_flag":"matched","comparison_group":f"tier={tier}|team={team}","peer_supported":True,"peer_agent_count":3,"peer_fallback_level":"tier_team",
        "status":"resolved","reporting_month":"2025-01","reporting_quarter":"2025-Q1","channel":"chat","priority":"Normal","product_family":"Audio",
        "valid_for_csat":True,"csat_score_numeric":score,"valid_for_handle_time":True,"handle_time_minutes":60+score,
        "valid_for_sla":True,"sla_breach_flag":score<4}

def test_leave_one_agent_out_adjustment_expected_direction_and_no_self_leakage():
    data=[row("a",5) for _ in range(10)]+[row("b",3) for _ in range(10)]+[row("c",3) for _ in range(10)]
    results=adjusted_agent_metrics(data)
    a=next(r for r in results if r["agent_id"]=="a" and r["period_type"]=="full_available_period")
    assert a["raw_mean_csat"]==5
    assert a["peer_mean_csat"]==3
    assert a["csat_gap"]==2
    assert a["csat_distinct_peer_count"]==2
    assert a["csat_adjustment_coverage_count"]==10
    reversed_a=next(r for r in adjusted_agent_metrics(list(reversed(data))) if r["agent_id"]=="a" and r["period_type"]=="full_available_period")
    assert reversed_a["peer_mean_csat"]==a["peer_mean_csat"]

def test_tier_two_peer_pool_stays_separate():
    data=[row(a,s,tier="1") for a,s in (("a",5),("b",3),("c",3)) for _ in range(10)]+[row(a,s,"Escalations","2") for a,s in (("d",2),("e",4),("f",4)) for _ in range(10)]
    results=adjusted_agent_metrics(data)
    d=next(r for r in results if r["agent_id"]=="d" and r["period_type"]=="full_available_period")
    assert d["peer_mean_csat"]==4
    assert d["csat_distinct_peer_count"]==2

def test_missing_product_family_falls_back_to_broader_context_cell():
    data=[row("a",5) for _ in range(6)]+[row("b",3) for _ in range(6)]+[row("c",3) for _ in range(6)]
    for r in data:
        r["product_family"]=None if r["agent_id"]=="a" else "Audio"
    a=next(r for r in adjusted_agent_metrics(data) if r["agent_id"]=="a" and r["period_type"]=="full_available_period")
    assert a["csat_adjustment_coverage_count"]==6
    assert a["csat_fallback_level"]=="channel_priority_period"
