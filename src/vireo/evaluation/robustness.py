"""Deterministic cluster-bootstrap, temporal, peer and ranking sensitivity checks."""
from __future__ import annotations

from collections import Counter, defaultdict
from random import Random
from statistics import mean, pstdev


OUTCOMES = ("csat", "handle_time", "sla")


def _num(v):
    try:
        return float(v) if v is not None else None
    except (ValueError, TypeError):
        return None


def _metric(row, metric):
    if metric == "csat" and row.get("valid_for_csat"):
        return _num(row.get("csat_score_numeric"))
    if metric == "handle_time" and row.get("valid_for_handle_time"):
        return _num(row.get("handle_time_minutes"))
    if metric == "sla" and row.get("valid_for_sla"):
        return float(bool(row.get("sla_breach_flag")))
    return None


def _group(row, mode):
    vals = [str(row.get("agent_tier") or "missing")]
    if mode in ("tier_team_site_shift", "tier_team_site", "tier_team"):
        vals.append(str(row.get("agent_team") or "missing"))
    if mode in ("tier_team_site_shift", "tier_team_site"):
        vals.append(str(row.get("agent_site") or "missing"))
    if mode == "tier_team_site_shift":
        vals.append(str(row.get("agent_shift") or "missing"))
    return "|".join(vals)


def _summaries(records, group_mode="tier_team"):
    sums = defaultdict(lambda: {m: [0.0, 0] for m in OUTCOMES})
    keys = {}
    for row in records:
        if row.get("agent_assignment_flag") != "matched" or not row.get("agent_id") or not row.get("agent_tier"):
            continue
        aid = row["agent_id"]
        keys[aid] = _group(row, group_mode)
        for metric in OUTCOMES:
            value = _metric(row, metric)
            if value is not None:
                sums[aid][metric][0] += value
                sums[aid][metric][1] += 1
    means = {aid: {m: (sums[aid][m][0] / sums[aid][m][1] if sums[aid][m][1] else None) for m in OUTCOMES}
             for aid in sums}
    counts = {aid: {m: sums[aid][m][1] for m in OUTCOMES} for aid in sums}
    return means, counts, keys


def _leave_one_agent_gaps(means, keys):
    groups = defaultdict(list)
    for aid, key in keys.items():
        groups[key].append(aid)
    gaps = {}
    peer_counts = {}
    for aid, own in means.items():
        peers = [p for p in groups[keys[aid]] if p != aid]
        peer_counts[aid] = len(peers)
        gaps[aid] = {}
        for metric in OUTCOMES:
            vals = [means[p][metric] for p in peers if means[p][metric] is not None]
            gaps[aid][metric] = own[metric] - mean(vals) if own[metric] is not None and len(vals) >= 2 else None
    return gaps, peer_counts


def _adverse(metric, gap):
    return gap < 0 if metric == "csat" else gap > 0


def clustered_customer_bootstrap(tickets, replicates=80, seed=1701, minimum_n=30):
    """Resample whole customer clusters; report point-direction proxy and percentile intervals."""
    customer_rows = defaultdict(list)
    for row in tickets:
        customer = row.get("customer_id") or f"__ticket__{row.get('ticket_id')}"
        customer_rows[customer].append(row)
    customers = sorted(customer_rows)
    if not customers:
        return [], []
    rng = Random(seed)
    gaps_by_agent = defaultdict(lambda: {m: [] for m in OUTCOMES})
    resample_rows = []
    candidate_hits = Counter()
    top_hits = Counter()
    rank_samples = defaultdict(list)
    for iteration in range(replicates):
        multiplicity = Counter(rng.choices(customers, k=len(customers)))
        sums = defaultdict(lambda: {m: [0.0, 0] for m in OUTCOMES})
        keys = {}
        for customer, weight in multiplicity.items():
            for row in customer_rows[customer]:
                if row.get("agent_assignment_flag") != "matched" or not row.get("agent_id") or not row.get("agent_tier"):
                    continue
                aid = row["agent_id"]
                keys[aid] = _group(row, "tier_team")
                for metric in OUTCOMES:
                    val = _metric(row, metric)
                    if val is not None:
                        sums[aid][metric][0] += val * weight
                        sums[aid][metric][1] += weight
        means = {aid: {m: (sums[aid][m][0] / sums[aid][m][1] if sums[aid][m][1] else None) for m in OUTCOMES}
                 for aid in sums}
        gaps, peer_counts = _leave_one_agent_gaps(means, keys)
        scores, directions = {}, {}
        for aid, outcome_gaps in gaps.items():
            adverse = {m: bool(outcome_gaps[m] is not None and _adverse(m, outcome_gaps[m]) and sums[aid][m][1] >= minimum_n) for m in OUTCOMES}
            directions[aid] = adverse
            # Exploratory two-signal proxy, deliberately separate from Stage 6 interval-gated decisions.
            score = sum(float(adverse[m]) * (0.4 if m == "csat" else 0.35 if m == "handle_time" else 0.25) for m in OUTCOMES)
            scores[aid] = score
            for metric in OUTCOMES:
                if outcome_gaps[metric] is not None:
                    gaps_by_agent[aid][metric].append(outcome_gaps[metric])
            if sum(adverse.values()) >= 2 and peer_counts.get(aid, 0) >= 2:
                candidate_hits[aid] += 1
        groups = defaultdict(list)
        for aid, score in scores.items():
            groups[keys[aid]].append(aid)
        iteration_candidates = set()
        for group, ids in groups.items():
            order = sorted(ids, key=lambda aid: (-scores[aid], aid))
            top_hits.update(order[:min(10, len(order))])
            for rank, aid in enumerate(order, 1):
                rank_samples[aid].append(rank)
                candidate = sum(directions[aid].values()) >= 2 and peer_counts.get(aid, 0) >= 2
                if candidate:
                    iteration_candidates.add(aid)
                resample_rows.append({"replicate": iteration + 1, "agent_id": aid, "comparison_group": group,
                    "candidate_proxy": candidate, "priority_band_proxy": "exploratory_concern" if candidate else "monitor",
                    "rank_by_adverse_signal_count": rank, "adverse_signal_count": sum(directions[aid].values()),
                    **{f"{m}_gap": gaps[aid][m] for m in OUTCOMES}})
        # A per-replicate candidate set is retained in report metadata by aggregate inclusion frequencies.
    summary = []
    for aid in sorted(set(rank_samples) | set(gaps_by_agent)):
        item = {"agent_id": aid, "candidate_inclusion_frequency": candidate_hits[aid] / replicates,
            "top10_inclusion_frequency": top_hits[aid] / replicates,
            "mean_group_rank": mean(rank_samples[aid]) if rank_samples[aid] else None,
            "rank_standard_deviation": pstdev(rank_samples[aid]) if len(rank_samples[aid]) > 1 else 0.0,
            "bootstrap_method": "customer_cluster_resampling_with_replacement"}
        for metric in OUTCOMES:
            vals = sorted(gaps_by_agent[aid][metric])
            lo = vals[int(.025 * (len(vals)-1))] if vals else None
            hi = vals[int(.975 * (len(vals)-1))] if vals else None
            item[f"{metric}_gap_ci_lower"] = lo
            item[f"{metric}_gap_ci_upper"] = hi
            item[f"{metric}_bootstrap_replicates"] = len(vals)
            item[f"{metric}_bootstrap_interval_adverse"] = (hi < 0 if metric == "csat" else lo > 0) if lo is not None and hi is not None else False
        item["bootstrap_supported_adverse"] = any(item[f"{m}_bootstrap_interval_adverse"] for m in OUTCOMES)
        summary.append(item)
    return summary, resample_rows


def temporal_leave_one_quarter_out(tickets, full_priority_ids=()):
    quarters = sorted({r.get("reporting_quarter") for r in tickets if r.get("reporting_quarter")})
    rows = []
    for quarter in quarters:
        kept = [r for r in tickets if r.get("reporting_quarter") != quarter]
        means, counts, keys = _summaries(kept)
        gaps, peer_counts = _leave_one_agent_gaps(means, keys)
        for aid, value in gaps.items():
            adverse = [m for m, gap in value.items() if gap is not None and _adverse(m, gap) and counts[aid][m] >= 30]
            rows.append({"excluded_quarter": quarter, "agent_id": aid, "comparison_group": keys[aid],
                "csat_gap": value["csat"], "handle_time_gap": value["handle_time"], "sla_gap": value["sla"],
                "adverse_point_signal_count": len(adverse), "candidate_proxy": len(adverse) >= 2 and peer_counts.get(aid, 0) >= 2,
                "full_stage6_candidate": aid in full_priority_ids, "peer_agent_count": peer_counts.get(aid, 0),
                "interpretation": "leave-one-quarter-out directional sensitivity; no interval-gated candidate decision"})
    return rows


def peer_group_robustness(tickets, default_candidate_ids=()):
    definitions = ("tier_team_site_shift", "tier_team_site", "tier_team", "tier")
    rows = []
    sets = {}
    support = {}
    for definition in definitions:
        means, counts, keys = _summaries(tickets, definition)
        gaps, peer_counts = _leave_one_agent_gaps(means, keys)
        candidates = set()
        for aid, metrics in gaps.items():
            adverse = [m for m, gap in metrics.items() if gap is not None and _adverse(m, gap) and counts[aid][m] >= 30]
            proxy = len(adverse) >= 2 and peer_counts.get(aid, 0) >= 2
            if proxy:
                candidates.add(aid)
            rows.append({"peer_definition": definition, "agent_id": aid, "comparison_group": keys[aid],
                "supported_peer_count": peer_counts.get(aid, 0), "csat_gap": metrics["csat"],
                "handle_time_gap": metrics["handle_time"], "sla_gap": metrics["sla"],
                "adverse_point_signal_count": len(adverse), "candidate_proxy": proxy,
                "stage6_candidate": aid in set(default_candidate_ids),
                "interpretation": "tier-safe leave-one-agent-out means; point-signal proxy, not Stage 6 inference"})
        sets[definition] = candidates
        support[definition] = {"agents_with_two_or_more_peers": sum(v >= 2 for v in peer_counts.values()),
                               "agents_evaluated": len(means), "point_signal_candidate_count": len(candidates)}
    for row in rows:
        other = [s for name, s in sets.items() if name != row["peer_definition"]]
        combined = set.union(*other) if other else set()
        here = sets[row["peer_definition"]]
        union = here | combined
        row["jaccard_vs_other_definitions"] = len(here & combined) / len(union) if union else 1.0
    return rows, support
