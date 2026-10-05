import pytest
from vireo.ai.schemas import SchemaValidationError, validate_ticket_result


def _result(**kwargs):
    value={"ticket_id":"t1","issue_category":"unclear","secondary_category":"unclear","customer_intent":"unclear",
        "diagnostic_theme":"insufficient_evidence","customer_problem":"unclear","resolution_pattern":"unclear",
        "communication_issue":"unclear","policy_process_issue":"unclear","possible_failure_theme":"unclear",
        "evidence":"","evidence_strength":"insufficient","confidence":0.1}
    return {**value,**kwargs}


def test_valid_and_uncertain_results():
    assert validate_ticket_result(_result(),"t1",[])['issue_category']=="unclear"
    assert validate_ticket_result(_result(issue_category="other"),"t1",[])['issue_category']=="other"


@pytest.mark.parametrize("changes", [{"issue_category":"invented"},{"confidence":1.1},{"confidence":True}, {"possible_failure_theme":"agent caused the refund"}])
def test_invalid_categories_confidence_and_causality(changes):
    with pytest.raises(SchemaValidationError): validate_ticket_result(_result(**changes),"t1",[])


def test_required_fields_ticket_id_and_evidence_are_checked():
    missing=_result(); missing.pop("evidence")
    with pytest.raises(SchemaValidationError): validate_ticket_result(missing,"t1",[])
    with pytest.raises(SchemaValidationError): validate_ticket_result(_result(ticket_id="other"),"t1",[])
    with pytest.raises(SchemaValidationError): validate_ticket_result(_result(evidence="made up"),"t1",["source text"])
