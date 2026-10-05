"""Strict runtime validation for model outputs without a runtime schema dependency."""
from __future__ import annotations

ISSUE_CATEGORIES = frozenset({"Delivery & Shipping", "Billing & Payments", "Charging & Battery", "Returns & Refunds",
    "Connectivity", "Warranty & Repair", "Audio Quality", "App & Firmware", "Product Enquiry", "Account & Login",
    "Other", "other", "unclear", "insufficient_evidence"})
CUSTOMER_INTENTS = frozenset({"troubleshooting", "status_update", "refund_or_replacement", "account_help",
    "product_information", "billing_help", "other", "unclear", "insufficient_evidence"})
DIAGNOSTIC_THEMES = frozenset({"product_knowledge", "policy_knowledge", "resolution_workflow", "escalation_handling",
    "communication_clarity", "expectation_management", "troubleshooting", "no_recurring_theme", "unclear", "insufficient_evidence"})
EVIDENCE_STRENGTHS = frozenset({"low", "moderate", "high", "insufficient"})
REQUIRED_FIELDS = {"ticket_id", "issue_category", "secondary_category", "customer_intent", "diagnostic_theme",
    "customer_problem", "resolution_pattern", "communication_issue", "policy_process_issue", "possible_failure_theme",
    "evidence", "evidence_strength", "confidence"}


class SchemaValidationError(ValueError):
    pass


def validate_ticket_result(value, ticket_id: str, evidence_sources: list[str]) -> dict:
    if not isinstance(value, dict):
        raise SchemaValidationError("model output must be a JSON object")
    missing = REQUIRED_FIELDS - value.keys()
    extra = value.keys() - REQUIRED_FIELDS
    if missing or extra:
        raise SchemaValidationError(f"schema fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")
    if value["ticket_id"] != ticket_id:
        raise SchemaValidationError("model returned a ticket ID outside the request")
    if value["issue_category"] not in ISSUE_CATEGORIES:
        raise SchemaValidationError("invalid issue_category")
    if value["secondary_category"] not in ISSUE_CATEGORIES:
        raise SchemaValidationError("invalid secondary_category")
    if value["customer_intent"] not in CUSTOMER_INTENTS:
        raise SchemaValidationError("invalid customer_intent")
    if value["diagnostic_theme"] not in DIAGNOSTIC_THEMES:
        raise SchemaValidationError("invalid diagnostic_theme")
    if value["evidence_strength"] not in EVIDENCE_STRENGTHS:
        raise SchemaValidationError("invalid evidence_strength")
    if isinstance(value["confidence"], bool) or not isinstance(value["confidence"], (float, int)) or not 0 <= value["confidence"] <= 1:
        raise SchemaValidationError("confidence must be numeric and between 0 and 1")
    for field in REQUIRED_FIELDS - {"ticket_id", "confidence"}:
        if not isinstance(value[field], str):
            raise SchemaValidationError(f"{field} must be a string")
        if len(value[field]) > 500:
            raise SchemaValidationError(f"{field} exceeds the maximum length")
    evidence = value["evidence"]
    if evidence and (len(evidence) > 280 or not any(evidence in text for text in evidence_sources)):
        raise SchemaValidationError("evidence must be a short exact span from supplied text")
    if value["issue_category"] == "insufficient_evidence" and evidence:
        raise SchemaValidationError("insufficient evidence output must not cite an evidence span")
    serialized = " ".join(value[k] for k in REQUIRED_FIELDS if isinstance(value[k], str)).casefold()
    if any(term in serialized for term in ("agent caused", "caused by agent", "agent fault", "because of the agent")):
        raise SchemaValidationError("unsupported causal attribution language")
    return {**value, "confidence": float(value["confidence"])}
