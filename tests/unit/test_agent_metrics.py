from vireo.analytics.agent_metrics import agent_assignment_metrics, agent_metrics

def ticket(agent, team, name, assignment="matched"):
    return {"agent_id":agent,"agent_name":name,"agent_team":team,"agent_tier":"1","agent_site":"Pune","agent_shift":"Day","agent_from_date":"2025-01-01","agent_to_date":"",
            "agent_assignment_flag":assignment,"status":"resolved","attendance_flag":True,"valid_for_csat":False,"csat_score_numeric":None,
            "valid_for_handle_time":False,"handle_time_minutes":None,"valid_for_first_response":False,"first_response_minutes":None,
            "sla_status":"not_evaluable","valid_for_transfers":True,"transfers_numeric":0,"text_quality_flag":"usable"}

def test_agent_ids_not_names_and_assignment_context_remains_distinct():
    rows = [ticket("a1","Chat","Same Name"),ticket("a2","Email","Same Name"),ticket("a1",None,"Same Name","no_roster_interval")]
    agents = agent_metrics(rows)
    assert len(agents) == 2
    assert {r["agent_id"] for r in agents} == {"a1","a2"}
    assignments = agent_assignment_metrics(rows)
    assert len(assignments) == 3
    assert sum(r["ticket_count"] for r in assignments) == 3
    assert sum(r["unmatched_roster_ticket_count"] for r in assignments) == 1
