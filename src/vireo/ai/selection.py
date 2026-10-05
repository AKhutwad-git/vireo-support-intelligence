"""Deterministic, configurable AI candidate selection from Stage 1-4 signals."""
from __future__ import annotations
import random
from statistics import quantiles

DEFAULT_SIGNALS = ("low_csat", "high_handle_time", "sla_breach", "repeat_contact", "refund_or_replacement", "multiple_transfers")


def _number(value):
    try: return float(value) if value not in (None, "") else None
    except (TypeError, ValueError): return None


def eligible_text_sources(row):
    quality = row.get("text_quality_flag") or "missing"
    msg = (row.get("customer_message") or "").strip()
    notes = (row.get("agent_notes") or "").strip()
    if quality == "usable" and msg:
        return quality, msg[:2000], notes[:2000]
    if notes:
        return quality, "", notes[:2000]
    return quality, "", ""


def score_candidates(rows, signals=DEFAULT_SIGNALS):
    handles = [_number(r.get("handle_time_minutes")) for r in rows if r.get("valid_for_handle_time") and _number(r.get("handle_time_minutes")) is not None]
    cutoff = quantiles(handles, n=10, method="inclusive")[-1] if len(handles) >= 10 else float("inf")
    scored = []
    for row in rows:
        text_quality, customer_text, notes = eligible_text_sources(row)
        if not customer_text and not notes:
            continue
        hits = []
        if "low_csat" in signals and row.get("valid_for_csat") and row.get("csat_score_numeric") is not None and row["csat_score_numeric"] <= 2: hits.append("low_csat")
        if "high_handle_time" in signals and row.get("valid_for_handle_time") and (_number(row.get("handle_time_minutes")) or 0) >= cutoff: hits.append("high_handle_time")
        if "sla_breach" in signals and row.get("sla_breach_flag"): hits.append("sla_breach")
        if "repeat_contact" in signals and row.get("repeat_contact_candidate_flag"): hits.append("repeat_contact")
        if "refund_or_replacement" in signals and (_number(row.get("refund_amount_inr")) or 0) > 0 or ("refund_or_replacement" in signals and row.get("replacement_issued_flag")): hits.append("refund_or_replacement")
        if "multiple_transfers" in signals and _number(row.get("transfers_numeric")) is not None and int(row["transfers_numeric"]) >= 2: hits.append("multiple_transfers")
        if hits:
            scored.append({**row, "text_quality_state": text_quality, "analysis_customer_text": customer_text,
                "analysis_agent_notes": notes, "selection_signals": sorted(set(hits)), "candidate_score": len(set(hits))})
    return scored


def select_candidates(rows, mode="top_n", max_population=250, top_n=250, sample_size=100,
                      random_seed=1701, agent_id=None, peer_group=None, signals=DEFAULT_SIGNALS):
    if max_population < 0 or top_n < 0 or sample_size < 0: raise ValueError("selection limits cannot be negative")
    candidates = score_candidates(rows, signals)
    if mode == "agent_sample": candidates = [r for r in candidates if r.get("agent_id") == agent_id]
    elif mode == "peer_sample": candidates = [r for r in candidates if r.get("comparison_group") == peer_group]
    elif mode not in {"all", "top_n", "sampled"}: raise ValueError(f"unknown candidate selection mode: {mode}")
    if mode == "top_n":
        candidates.sort(key=lambda r: (-r["candidate_score"], r["ticket_id"]))
        candidates = candidates[:top_n]
    elif mode == "sampled": candidates = sorted(random.Random(random_seed).sample(candidates, min(sample_size, len(candidates))), key=lambda r: r["ticket_id"])
    elif mode in {"agent_sample", "peer_sample"}:
        candidates.sort(key=lambda r: (-r["candidate_score"], r["ticket_id"]))
        candidates = candidates[:sample_size]
    else: candidates.sort(key=lambda r: r["ticket_id"])
    return candidates[:max_population]
