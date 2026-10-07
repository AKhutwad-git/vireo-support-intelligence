"""Descriptive management-review lists, separate from Stage 6 decisions."""
from __future__ import annotations

from math import isfinite


def _number(value):
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


def review_score_fields(comparison: dict, config: dict) -> dict:
    """Score peer-adjusted point estimates on fixed, documented scales.

    A positive score is favorable; a negative score is adverse. Each gap is
    relative to the agent's supported Tier-safe peer baseline. The score is
    descriptive only and never changes Stage 6 priority or its evidence gate.
    """
    if comparison.get("peer_supported") is not True or comparison.get("comparison_status") != "comparable":
        return {"review_score": None, "review_score_metric_count": 0,
                "review_score_components": {}, "review_score_status": "no_supported_peer_comparison"}

    weights = config.get("metric_weights", {"csat": 0.40, "handle_time": 0.35, "sla": 0.25})
    scales = {
        "csat": _number(config.get("csat_gap_scale")) or 0.5,
        "handle_time": _number(config.get("handle_time_relative_gap_scale")) or 0.25,
        "sla": _number(config.get("sla_gap_scale")) or 0.05,
    }
    raw = {}
    gap = _number(comparison.get("csat_gap"))
    if gap is not None and scales["csat"] > 0:
        raw["csat"] = max(-1.0, min(1.0, gap / scales["csat"]))

    gap = _number(comparison.get("handle_time_gap"))
    peer = _number(comparison.get("peer_handle_time_mean"))
    if gap is not None and peer is not None and peer > 0 and scales["handle_time"] > 0:
        raw["handle_time"] = max(-1.0, min(1.0, -(gap / peer) / scales["handle_time"]))

    gap = _number(comparison.get("sla_gap"))
    if gap is not None and scales["sla"] > 0:
        raw["sla"] = max(-1.0, min(1.0, -gap / scales["sla"]))

    valid_weights = {name: max(0.0, _number(weights.get(name)) or 0.0)
                     for name in raw}
    denominator = sum(valid_weights.values())
    if not raw or denominator <= 0:
        return {"review_score": None, "review_score_metric_count": 0,
                "review_score_components": {}, "review_score_status": "no_supported_metric_gaps"}

    score = 100.0 * sum(raw[name] * valid_weights[name] for name in raw) / denominator
    return {"review_score": round(score, 6), "review_score_metric_count": len(raw),
            "review_score_components": {name: round(value * 100.0, 4) for name, value in raw.items()},
            "review_score_status": "descriptive_peer_adjusted_review_only"}


def build_review_lists(rows: list[dict], *, bottom_limit: int = 10, top_limit: int = 5) -> dict:
    """Select deterministic review queues without altering training status."""
    if bottom_limit < 0 or top_limit < 0:
        raise ValueError("Review-list limits must be non-negative")
    eligible = [dict(row) for row in rows
                if row.get("peer_supported") is True
                and row.get("comparison_status") == "comparable"
                and _number(row.get("review_score")) is not None]
    bottom = sorted(eligible, key=lambda row: (_number(row["review_score"]), str(row.get("agent_id", ""))))[:bottom_limit]
    top = sorted(eligible, key=lambda row: (-_number(row["review_score"]), str(row.get("agent_id", ""))))[:top_limit]
    for rank, row in enumerate(bottom, 1):
        row["review_list_rank"] = rank
    for rank, row in enumerate(top, 1):
        row["review_list_rank"] = rank
    return {"bottom10_review": bottom, "top5_bonus_review": top,
            "ranked_agent_count": len(eligible),
            "definition": "Weighted mean of peer-adjusted CSAT, handle-time, and SLA gaps normalized to configured Stage 6 scales, each capped to [-1, 1], then expressed on a -100 to +100 scale. Positive is favorable. Peer baselines remain Tier-safe; this is a review queue, not a training or bonus recommendation. Ties break by agent_id."}
