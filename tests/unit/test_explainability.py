from tests.unit.test_training_priority import fixture_rows
from vireo.scoring.priority import build_priority_rows


def test_explanations_expose_gaps_economic_caution_and_no_ai_penalty():
    comp,agents,econ=fixture_rows()
    row=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    assert row["explanation"]["agent_id"]=="A1"
    assert row["economic_context"]["training_cost_inr"] is None
    assert "not savings" in row["economic_context"]["label"]
    assert any("does not reduce deterministic priority" in item for item in row["limitations"])
    assert row["representative_ticket_ids"]==[]


def test_partial_and_failed_ai_status_are_reported_without_changing_score():
    comp,agents,econ=fixture_rows()
    ai=[{"agent_id":"A1","training_topics":["policy knowledge"],"representative_ticket_ids":["T1"]}]
    available=build_priority_rows(comp,agents,econ,ai,"available",{})[0]
    partial=build_priority_rows(comp,agents,econ,ai,"partial",{})[0]
    failed=build_priority_rows(comp,agents,econ,ai,"failed",{})[0]
    assert partial["ai_evidence_status"]=="partial"
    assert failed["ai_evidence_status"]=="failed"
    assert partial["priority_score"]==available["priority_score"]==failed["priority_score"]
