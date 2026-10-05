from vireo.analytics.stability import assess_stability

def record(period,mean,lo,hi):
    return {"agent_id":"a","agent_team":"T","agent_tier":"1","agent_site":"P","agent_shift":"D","agent_from_date":"2025-01-01","agent_to_date":"","period_type":"quarter","period":period,"outcome":"csat","eligible_count":20,"mean":mean,"ci_lower":lo,"ci_upper":hi}

def test_stable_and_changing_synthetic_agents():
    stable=assess_stability([record("2025-Q1",3,2.5,3.5),record("2025-Q2",3.1,2.6,3.6),record("2025-Q3",3,2.5,3.5)])
    assert stable[0]["stability_flag"]=="no_clear_shift_detected"
    changed=assess_stability([record("2025-Q1",2,1.8,2.2),record("2025-Q2",4.5,4.3,4.7)])
    assert changed[0]["stability_flag"]=="variable_across_quarters"

def test_one_period_is_insufficient_for_stability():
    assert assess_stability([record("2025-Q1",3,2,4)])[0]["stability_flag"]=="insufficient_period_evidence"
