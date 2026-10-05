from vireo.ai.selection import select_candidates


def _row(tid, **kw):
    base={"ticket_id":tid,"agent_id":"a1","channel":"chat","text_quality_flag":"usable","customer_message":"help me", "agent_notes":"reset advised",
        "valid_for_csat":True,"csat_score_numeric":1,"valid_for_handle_time":True,"handle_time_minutes":5,
        "sla_breach_flag":False,"repeat_contact_candidate_flag":False,"refund_amount_inr":0,"replacement_issued_flag":False,"transfers_numeric":"0"}
    return {**base,**kw}


def test_selection_is_deterministic_and_capped():
    rows=[_row(f"t{i}",csat_score_numeric=i%5+1,sla_breach_flag=i%2==0) for i in range(20)]
    a=select_candidates(rows,mode="top_n",max_population=4,top_n=10)
    b=select_candidates(rows,mode="top_n",max_population=4,top_n=10)
    assert [r["ticket_id"] for r in a]==[r["ticket_id"] for r in b]
    assert len(a)==4


def test_sampled_selection_reproducible_and_degraded_text_excluded():
    rows=[_row(f"t{i}",text_quality_flag="degraded",customer_message="[IVR junk]",agent_notes="note") for i in range(5)]
    first=select_candidates(rows,mode="sampled",sample_size=3,max_population=3)
    second=select_candidates(rows,mode="sampled",sample_size=3,max_population=3)
    assert [r["ticket_id"] for r in first]==[r["ticket_id"] for r in second]
    assert all(not r["analysis_customer_text"] and r["analysis_agent_notes"]=="note" for r in first)
    assert select_candidates([_row("empty",customer_message="",agent_notes="")],mode="all")==[]
