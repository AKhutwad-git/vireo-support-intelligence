from vireo.data.validators import validate_categories, validate_key, validate_numeric_ranges, validate_required_columns, validate_table


def statuses(checks):
    return {check.name: check.status for check in checks}


def test_valid_schema_passes():
    assert statuses(validate_required_columns("tickets", [{"ticket_id": "t1", "created_at": "2026-01-01"}], ["ticket_id", "created_at"]))["required_columns"] == "PASS"


def test_missing_required_column_fails():
    assert statuses(validate_required_columns("tickets", [{"ticket_id": "t1"}], ["ticket_id", "created_at"]))["required_columns"] == "FAIL"


def test_duplicate_critical_key_is_detected():
    assert statuses(validate_key("tickets", [{"ticket_id": "t1"}, {"ticket_id": "t1"}], "ticket_id"))["duplicate_key"] == "FAIL"


def test_null_critical_identifier_is_detected():
    assert statuses(validate_key("tickets", [{"ticket_id": ""}], "ticket_id"))["critical_identifier_nulls"] == "FAIL"


def test_invalid_date_is_detected():
    checks = validate_table("tickets", [{"created_at": "not-a-date"}], date_columns=["created_at"])
    assert statuses(checks)["date_parse"] == "FAIL"


def test_configured_numeric_bounds_and_categories_are_checked():
    row = {"amount": "-2", "state": "mystery"}
    assert statuses(validate_numeric_ranges("orders", [row], {"amount": {"min": 0}}))["numeric_range"] == "FAIL"
    assert statuses(validate_categories("tickets", [row], {"state": ["open", "closed"]}))["categorical_values"] == "FAIL"
