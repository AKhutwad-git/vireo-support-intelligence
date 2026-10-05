"""Deterministic normalization and canonical Parquet output generation."""
from __future__ import annotations
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import json

from vireo.data.cleaning import normalize_table
from vireo.data.temporal import assign_roster, normalize_ticket_timestamp
from vireo.data.text_quality import classify_message
from vireo.data.reconciliation import flag_duplicate_candidates
from vireo.data.validators import validate_relationship


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows) if rows else pa.table({})
    pq.write_table(table, path, compression="zstd")


def _parsed(value: str | None):
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def preprocess(tables: dict[str, list[dict[str, Any]]], interim_dir: Path) -> dict[str, Any]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    changes: dict[str, list[dict[str, Any]]] = {}
    for name, rows in tables.items():
        normalized[name], changes[name] = normalize_table(rows)

    tickets = normalized.get("tickets", [])
    roster = normalized.get("agents", [])
    customer_by_id = {r["customer_id"]: r for r in normalized.get("customers", [])}
    product_by_sku = {r["sku"]: r for r in normalized.get("products", [])}
    order_by_id = {r["order_id"]: r for r in normalized.get("orders", [])}
    outputs: dict[str, Any] = {}

    if tickets:
        prepared = []
        for row in tickets:
            item = dict(row)
            item["created_at_raw"] = row.get("created_at") or ""
            item["first_response_at_raw"] = row.get("first_response_at") or ""
            item["resolved_at_raw"] = row.get("resolved_at") or ""
            applied = False
            for field in ("created_at", "first_response_at", "resolved_at"):
                value, assumed_zone = normalize_ticket_timestamp(row.get(field), row.get("source_system", ""), field)
                item[field] = value
                applied |= assumed_zone
            item["timestamp_normalization_applied"] = applied
            item["timestamp_normalization_reason"] = "legacy_resolved_utc" if row.get("source_system") == "legacy_fd" else "helpdesk_ist"
            assignment = assign_roster(item, roster)
            for col in ("name", "site", "team", "shift", "tier", "from_date", "to_date"):
                item[f"agent_{col}"] = (assignment or {}).get(col)
            item["agent_assignment_flag"] = "matched" if assignment else ("missing_agent_or_time" if not row.get("agent_id") or not item.get("resolved_at") else "no_roster_interval")
            quality, reason = classify_message(row.get("customer_message"), row.get("channel"))
            item["text_quality_flag"] = quality
            item["text_quality_reason"] = reason
            customer = customer_by_id.get(row.get("customer_id"), {})
            order = order_by_id.get(row.get("order_id"), {}) if row.get("order_id") else {}
            if not order and row.get("customer_id") and row.get("product_sku"):
                candidates = [o for o in normalized.get("orders", []) if o.get("customer_id") == row.get("customer_id") and o.get("sku") == row.get("product_sku")]
                # Deliberately retain ambiguity rather than picking an arbitrary order.
                if len(candidates) == 1:
                    order = candidates[0]
            signup = _parsed(customer.get("signup_date"))
            order_date = _parsed(order.get("order_date"))
            launch = _parsed(product_by_sku.get(row.get("product_sku"), {}).get("launch_date"))
            created = _parsed(item.get("created_at"))
            item["signup_anomaly_flag"] = bool(signup and order_date and order_date.date() < signup.date())
            item["product_prelaunch_anomaly_flag"] = bool(launch and created and created.date() < launch.date())
            item["order_match_flag"] = "matched" if order else ("missing_order_id" if not row.get("order_id") else "unmatched_order")
            prepared.append(item)
        tickets = flag_duplicate_candidates(prepared)
        normalized["tickets"] = tickets

    for name, rows in normalized.items():
        target = interim_dir / f"normalized_{name}.parquet"
        write_parquet(target, rows)
        outputs[name] = {"path": str(target), "row_count": len(rows)}
    if changes:
        interim_dir.mkdir(parents=True, exist_ok=True)
        (interim_dir / "normalization_changes.json").write_text(json.dumps(changes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Explicit relationship findings; nullable order_id is expected by the source definition.
    join_findings = {}
    for parent, child, pk, fk in (("customers", "tickets", "customer_id", "customer_id"), ("products", "tickets", "sku", "product_sku"), ("orders", "tickets", "order_id", "order_id")):
        if parent in normalized and child in normalized:
            facts = [r for r in normalized[child] if r.get(fk)]
            join_findings[f"{parent}_to_{child}"] = [c.__dict__ for c in validate_relationship(parent, child, normalized[parent], facts, pk, fk)]
    return {"outputs": outputs, "changes": changes, "join_findings": join_findings}
