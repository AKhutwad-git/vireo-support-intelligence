from tests.unit.test_training_priority import fixture_rows
from vireo.scoring.priority import build_priority_rows


def test_missing_peer_and_low_evidence_are_not_ranked():
    comp,agents,econ=fixture_rows()
    comp[0].update(peer_supported=False,comparison_group=None,comparison_status="no_supported_peer")
    out=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    assert out["priority_status"]=="not_rankable"
    assert "no_comparable_peer" in out["eligibility_gates"]

    comp,agents,econ=fixture_rows()
    comp[0]["csat_eligible_count"]=4
    out=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    assert out["priority_status"]=="not_rankable"
    assert "insufficient_evidence" in out["eligibility_gates"]


def test_unstable_and_data_quality_restrictions_propagate():
    comp,agents,econ=fixture_rows()
    comp[0]["stability_flag"]="variable_across_quarters"
    comp[0]["sla_adjustment_coverage_rate"]=.4
    out=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    assert "unstable" in out["eligibility_gates"]
    assert "data_quality_restricted" in out["eligibility_gates"]


def test_tier_mismatched_peer_group_is_blocked():
    comp,agents,econ=fixture_rows()
    comp[0]["agent_tier"]="2"
    comp[0]["comparison_group"]="tier=1|team=Chat Frontline"
    out=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    assert out["priority_status"]=="not_rankable"
    assert "invalid_tier_peer" in out["eligibility_gates"]
