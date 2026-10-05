from tests.unit.test_training_priority import fixture_rows
from vireo.scoring.priority import _adverse, build_priority_rows


def test_metric_direction_and_uncertainty_gate():
    comp,agents,econ=fixture_rows()
    row=comp[0]
    assert _adverse("csat",row) and _adverse("handle_time",row) and _adverse("sla",row)
    row["csat_gap_ci_lower"]=-2.; row["csat_gap_ci_upper"]=2.
    assert not _adverse("csat",row)
    assert _adverse("csat",row,require_interval=False)


def test_weaker_evidence_cannot_increase_evidence_strength_or_priority():
    comp,agents,econ=fixture_rows()
    strong=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    weaker=[dict(r) for r in comp]
    next(r for r in weaker if r["period_type"]=="full_available_period")["csat_eligible_count"]=15
    weak=build_priority_rows(weaker,agents,econ,[],"unavailable",{})[0]
    assert weak["evidence_strength"] in ("LOW","MEDIUM")
    assert weak["priority_score"] <= strong["priority_score"]


def test_ai_theme_does_not_change_numeric_priority_score():
    comp,agents,econ=fixture_rows()
    plain=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    ai=[{"agent_id":"A1","training_topics":["policy knowledge"],"representative_ticket_ids":["T1"]}]
    enriched=build_priority_rows(comp,agents,econ,ai,"available",{})[0]
    assert enriched["priority_score"]==plain["priority_score"]
    assert enriched["training_theme"]=="policy knowledge"
    assert enriched["priority_reason"]==plain["priority_reason"]


def test_conflicting_metrics_are_preserved_in_explanation():
    comp,agents,econ=fixture_rows()
    full=next(r for r in comp if r["period_type"]=="full_available_period")
    full["handle_time_gap_ci_lower"]=-80.; full["handle_time_gap_ci_upper"]=-10.
    full["handle_time_gap"]=-40.
    out=build_priority_rows(comp,agents,econ,[],"unavailable",{})[0]
    assert out["metric_directions"]["csat"]=="concern"
    assert out["metric_directions"]["handle_time"]=="favorable"
    assert out["diagnostic_state"]=="mixed_performance"
    assert "conflict" in out["priority_reason"]
