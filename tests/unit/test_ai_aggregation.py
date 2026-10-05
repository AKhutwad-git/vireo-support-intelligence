from vireo.ai.aggregation import aggregate_agent_diagnostics, aggregate_peer_diagnostics


def test_aggregation_uses_only_validated_completed_analyses():
    rows=[{"analysis_status":"analyzed","attendance_flag":True,"agent_id":"a1","ticket_id":"t1","issue_category":"Connectivity","diagnostic_theme":"troubleshooting","confidence":.8,"evidence_strength":"high"},
        {"analysis_status":"analyzed","attendance_flag":True,"agent_id":"a1","ticket_id":"t2","issue_category":"Connectivity","diagnostic_theme":"troubleshooting","confidence":.7,"evidence_strength":"high"},
        {"analysis_status":"provider_unavailable","attendance_flag":True,"agent_id":"a1","ticket_id":"t3","issue_category":"Billing & Payments"},
        {"analysis_status":"analyzed","attendance_flag":False,"agent_id":"a1","ticket_id":"t4","issue_category":"Connectivity"}]
    summary=aggregate_agent_diagnostics(rows)[0]
    assert summary["sample_size"]==2
    assert summary["training_topics"]==["troubleshooting"]
    assert summary["representative_ticket_ids"]==["t1","t2"]


def test_peer_diagnostics_require_supported_peer_context():
    rows=[{"analysis_status":"analyzed","attendance_flag":True,"peer_supported":True,"comparison_group":"tier=1|team=T","ticket_id":"t1","issue_category":"Connectivity","diagnostic_theme":"troubleshooting","confidence":.8,"evidence_strength":"high"},
        {"analysis_status":"analyzed","attendance_flag":True,"peer_supported":False,"comparison_group":None,"ticket_id":"t2","issue_category":"Connectivity","diagnostic_theme":"troubleshooting","confidence":.7,"evidence_strength":"high"}]
    result=aggregate_peer_diagnostics(rows)
    assert len(result)==1 and result[0]["sample_size"]==1
