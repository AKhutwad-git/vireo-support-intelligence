from vireo.data.temporal import assign_roster, normalize_ticket_timestamp
from vireo.data.text_quality import classify_message
from vireo.data.reconciliation import flag_duplicate_candidates


def test_source_aware_timestamp_rules():
    legacy, _ = normalize_ticket_timestamp("2025-09-14 00:00:00", "legacy_fd", "resolved_at")
    current, _ = normalize_ticket_timestamp("2025-09-14 00:00:00", "helpdesk", "resolved_at")
    assert legacy.endswith("00:00:00+00:00")
    assert current.endswith("18:30:00+00:00")


def test_effective_dated_roster_matches_by_id_and_time():
    rows = [{"agent_id": "a", "team": "old", "from_date": "2025-01-01", "to_date": "2025-06-30"},
            {"agent_id": "a", "team": "new", "from_date": "2025-07-01", "to_date": ""}]
    assert assign_roster({"agent_id": "a", "resolved_at": "2025-08-01T00:00:00+00:00"}, rows)["team"] == "new"


def test_text_quality_is_deterministic_and_ivrs_flagged():
    assert classify_message("IVR transcript failed due to technical issue", "voice") == ("degraded", "known_ivr_or_transcript_marker")
    assert classify_message("My headphones stopped working", "email")[0] == "usable"


def test_cross_source_duplicate_candidates_are_flags_only():
    rows = [{"customer_id": "c", "product_sku": "p", "created_at": "t", "source_system": "helpdesk"},
            {"customer_id": "c", "product_sku": "p", "created_at": "t", "source_system": "legacy_fd"}]
    flagged = flag_duplicate_candidates(rows)
    assert len(flagged) == 2
    assert all(row["reconciliation_flag"] for row in flagged)
