from vireo.scoring.review import build_review_lists, review_score_fields


CONFIG = {
    "metric_weights": {"csat": 0.40, "handle_time": 0.35, "sla": 0.25},
    "csat_gap_scale": 0.5,
    "handle_time_relative_gap_scale": 0.25,
    "sla_gap_scale": 0.05,
}


def _comparison(agent_id, score, tier="1", *, supported=True, csat=0.0):
    return {
        "agent_id": agent_id,
        "agent_tier": tier,
        "comparison_group": f"tier={tier}|team=Team {tier}",
        "peer_supported": supported,
        "comparison_status": "comparable" if supported else "no_comparable_peer",
        "csat_gap": csat,
        "peer_handle_time_mean": 100.0,
        "handle_time_gap": 0.0,
        "sla_gap": 0.0,
        "review_score": score,
        "priority_status": "monitor",
        "evidence_strength": "LOW",
    }


def test_review_score_is_peer_adjusted_weighted_and_bounded():
    row = _comparison("A1", 0, csat=0.5)
    row.update({"handle_time_gap": -100.0, "sla_gap": -0.05})
    result = review_score_fields(row, CONFIG)
    assert result["review_score"] == 100.0
    assert result["review_score_metric_count"] == 3
    assert result["review_score_status"] == "descriptive_peer_adjusted_review_only"

    row.update({"csat_gap": -5.0, "handle_time_gap": 1000.0, "sla_gap": 1.0})
    assert review_score_fields(row, CONFIG)["review_score"] == -100.0


def test_missing_metrics_and_small_evidence_do_not_crash_or_change_training_status():
    row = _comparison("A1", 0)
    row.update({"csat_gap": None, "handle_time_gap": None, "peer_handle_time_mean": None,
                "sla_gap": -0.01, "evidence_strength": "LOW", "priority_status": "monitor",
                "sample_size": 1})
    fields = review_score_fields(row, CONFIG)
    assert fields["review_score_metric_count"] == 1
    assert fields["review_score"] == 20.0
    assert row["priority_status"] == "monitor"


def test_review_queues_are_bounded_deterministic_and_keep_tier_safe_peer_context():
    rows = [_comparison(f"A{i:02}", i - 12, "1" if i % 2 else "2") for i in range(24)]
    rows.append(_comparison("UNSUPPORTED", -1000, supported=False))
    first = build_review_lists(rows)
    second = build_review_lists(list(reversed(rows)))
    assert len(first["bottom10_review"]) == 10
    assert len(first["top5_bonus_review"]) == 5
    assert [r["agent_id"] for r in first["bottom10_review"]] == [r["agent_id"] for r in second["bottom10_review"]]
    assert [r["agent_id"] for r in first["top5_bonus_review"]] == [r["agent_id"] for r in second["top5_bonus_review"]]
    for row in first["bottom10_review"] + first["top5_bonus_review"]:
        assert row["comparison_group"].startswith(f"tier={row['agent_tier']}|")
        assert row["priority_status"] == "monitor"
    assert "UNSUPPORTED" not in {r["agent_id"] for r in first["bottom10_review"] + first["top5_bonus_review"]}


def test_zero_and_one_eligible_agent_return_zero_or_one_row():
    assert build_review_lists([])["bottom10_review"] == []
    single = build_review_lists([_comparison("A1", 1)])
    assert [r["agent_id"] for r in single["bottom10_review"]] == ["A1"]
    assert [r["agent_id"] for r in single["top5_bonus_review"]] == ["A1"]
