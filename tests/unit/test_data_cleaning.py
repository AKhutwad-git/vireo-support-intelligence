from vireo.data.cleaning import normalize_table, normalize_value


def test_categorical_text_normalization_is_deterministic():
    assert normalize_value("  In   Progress  ") == "In Progress"
    assert normalize_value("  In   Progress  ") == normalize_value("  In   Progress  ")


def test_missing_spellings_are_standardized():
    assert normalize_value(" N/A ") == ""
    assert normalize_value(" NuLl ") == ""


def test_cleaning_preserves_row_count_and_logs_changes():
    source = [{"status": " open  ", "ticket_id": "1"}, {"status": "closed", "ticket_id": "2"}]
    cleaned, changes = normalize_table(source)
    assert len(cleaned) == len(source)
    assert cleaned[0]["status"] == "open"
    assert len(changes) == 1
    assert source[0]["status"] == " open  "
