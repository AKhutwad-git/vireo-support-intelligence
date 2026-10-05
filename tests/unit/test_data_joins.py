import pytest

from vireo.data.joins import validated_left_join


def test_validated_many_to_one_join_preserves_fact_rows():
    facts = [{"agent_id": "a1", "ticket_id": "t1"}, {"agent_id": "a1", "ticket_id": "t2"}]
    agents = [{"id": "a1", "name": "A"}]
    joined, checks = validated_left_join(facts, agents, "agent_id", "id", prefix="agent_")
    assert len(joined) == len(facts)
    assert [row["agent_name"] for row in joined] == ["A", "A"]
    assert all(check.status == "PASS" for check in checks)


def test_join_rejects_orphan_foreign_keys():
    with pytest.raises(ValueError, match="relationship validation"):
        validated_left_join([{"agent_id": "missing"}], [{"id": "a1"}], "agent_id", "id")


def test_join_rejects_duplicate_dimension_key():
    with pytest.raises(ValueError, match="dimension key is not unique"):
        validated_left_join([{"agent_id": "a1"}], [{"id": "a1"}, {"id": "a1"}], "agent_id", "id")
