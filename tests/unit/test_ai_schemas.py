import json
from pathlib import Path
import pytest
from vireo.ai.schemas import SchemaValidationError, validate_ticket_result
from vireo.ai.prompts import load_prompts
from scripts.run_real_ai_evaluation import _schema_diagnostic

ROOT = Path(__file__).resolve().parents[2]


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


@pytest.mark.parametrize("invalid,expected_type", [("very_high", "str"), (0.8, "float")])
def test_invalid_evidence_strength_is_rejected_with_safe_diagnostics(invalid, expected_type):
    output = _result(evidence_strength=invalid)
    with pytest.raises(SchemaValidationError) as caught:
        validate_ticket_result(output, "t1", [])

    diagnostic = _schema_diagnostic(caught.value, output)
    assert diagnostic["failure_stage"] == "schema_validation"
    assert diagnostic["validation_field"] == "evidence_strength"
    assert diagnostic["validation_error_type"] == "enum"
    assert diagnostic["received_value_type"] == expected_type
    assert diagnostic["constraint"]["allowed_values"] == ["high", "insufficient", "low", "moderate"]
    assert invalid.__str__() not in json.dumps(diagnostic)


def test_non_string_policy_process_issue_is_rejected_without_persisting_value():
    sensitive_value = {"customer_text": "SENSITIVE-CUSTOMER-CONTENT"}
    output = _result(policy_process_issue=sensitive_value)
    with pytest.raises(SchemaValidationError) as caught:
        validate_ticket_result(output, "t1", [])

    diagnostic = _schema_diagnostic(caught.value, output)
    assert diagnostic["failure_stage"] == "schema_validation"
    assert diagnostic["validation_field"] == "policy_process_issue"
    assert diagnostic["validation_error_type"] == "field_type"
    assert diagnostic["constraint"] == "string required"
    assert "SENSITIVE-CUSTOMER-CONTENT" not in json.dumps(diagnostic)


def test_prompt_v2_makes_output_contract_explicit():
    prompt = load_prompts(ROOT / "configs" / "prompts.yaml")["issue_classification_v1"]
    text = prompt["text"]
    assert prompt["version"] == "issue_classification_v2"
    assert '"high", "insufficient", "low", "moderate"' in text
    assert "exhaustive, case-sensitive set" in text
    assert "Do not use any other value" in text
    assert "policy_process_issue must always be a JSON string" in text
    assert 'exactly "unclear"' in text
    assert 'exactly "insufficient_evidence"' in text
