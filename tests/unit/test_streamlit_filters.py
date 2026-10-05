import pytest

from app.dashboard_data import filter_agent_rows, filter_value


def test_missing_peer_group_is_a_selectable_filter_bucket():
    rows = [
        {"agent_id": "A-01", "comparison_group": None, "agent_tier": "1"},
        {"agent_id": "A-02", "comparison_group": "Tier 1 · Billing", "agent_tier": "1"},
    ]
    selections = {
        "comparison_group": {filter_value(row["comparison_group"]) for row in rows},
        "agent_tier": {"1"},
    }

    assert filter_value(None) == "Unavailable"
    assert [row["agent_id"] for row in filter_agent_rows(rows, selections)] == ["A-01", "A-02"]
    assert [row["agent_id"] for row in filter_agent_rows(rows, {**selections, "comparison_group": {"Unavailable"}})] == ["A-01"]


@pytest.mark.parametrize("field", ["agent_tier", "agent_team", "agent_site", "agent_shift", "priority_status", "comparison_group"])
def test_each_categorical_filter_reduces_rows_to_the_selected_value(field):
    rows = [{"agent_id": "A-01", field: "selected"}, {"agent_id": "A-02", field: "other"}]

    assert [row["agent_id"] for row in filter_agent_rows(rows, {field: {"selected"}})] == ["A-01"]
