"""Conservative detectable repeat-contact candidates (not policy-defined FCR)."""
from __future__ import annotations
from datetime import datetime, timedelta
from bisect import bisect_left
from collections import defaultdict


def _dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def detect_repeat_contacts(rows: list[dict], window_days: int = 30) -> list[dict]:
    """Mark a later contact once when same customer/order or fallback SKU follows resolution."""
    if window_days <= 0:
        raise ValueError("window_days must be positive")
    indexed = []
    for row in rows:
        indexed.append({**row, "_created": _dt(row.get("created_at")), "_resolved": _dt(row.get("resolved_at"))})
    out = {r.get("ticket_id"): {"repeat_contact_candidate_flag": False,
                                "repeat_contact_prior_ticket_id": None,
                                "repeat_contact_match_method": None,
                                "repeat_contact_candidate_reason": "no_qualifying_prior_contact"} for r in indexed}
    buckets = defaultdict(list)
    for prior in indexed:
        if not prior["_resolved"] or not prior.get("customer_id"):
            continue
        order = prior.get("order_id")
        if order:
            key = (prior["customer_id"], "order", order)
        elif prior.get("product_sku"):
            key = (prior["customer_id"], "sku", prior["product_sku"])
        else:
            continue
        buckets[key].append((prior["_resolved"], str(prior.get("ticket_id") or ""), prior))
    for entries in buckets.values():
        entries.sort(key=lambda item: (item[0], item[1]))
    for subsequent in indexed:
        created = subsequent["_created"]
        customer = subsequent.get("customer_id")
        if not created or not customer:
            out[subsequent.get("ticket_id")]["repeat_contact_candidate_reason"] = "missing_created_at_or_customer_id"
            continue
        order = subsequent.get("order_id")
        sku = subsequent.get("product_sku")
        if order:
            key, method = (customer, "order", order), "customer_order_id"
        elif sku:
            key, method = (customer, "sku", sku), "customer_product_sku_fallback"
        else:
            out[subsequent.get("ticket_id")]["repeat_contact_candidate_reason"] = "missing_order_and_product_sku"
            continue
        entries = buckets.get(key, [])
        # Latest prior resolution strictly before contact and no older than the policy window.
        position = bisect_left(entries, (created, "")) - 1
        if position >= 0 and created - entries[position][0] <= timedelta(days=window_days):
            prior = entries[position][2]
            out[subsequent.get("ticket_id")] = {"repeat_contact_candidate_flag": True,
                "repeat_contact_prior_ticket_id": prior.get("ticket_id"),
                "repeat_contact_match_method": method,
                "repeat_contact_candidate_reason": "same_customer_issue_proxy_within_30_days"}
    return [{**r, **out[r.get("ticket_id")]} for r in rows]
