"""Lightweight, source-driven schema descriptions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

# Contract columns and keys taken directly from data/raw/README.txt.
SOURCE_CONTRACTS = {
    "tickets": {"key": "ticket_id", "required": "ticket_id created_at first_response_at resolved_at status channel customer_id order_id product_sku category priority assigned_team agent_id transfers csat_score refund_amount_inr refund_reason_code replacement_issued customer_message agent_notes source_system".split(), "dates": ["created_at", "first_response_at", "resolved_at"]},
    "agents": {"key": "agent_id", "required": "agent_id name site team shift tier from_date to_date".split(), "dates": ["from_date", "to_date"]},
    "customers": {"key": "customer_id", "required": "customer_id name city state signup_date care_plus".split(), "dates": ["signup_date"]},
    "orders": {"key": "order_id", "required": "order_id customer_id sku order_date channel qty order_value_inr lot_code".split(), "dates": ["order_date"]},
    "products": {"key": "sku", "required": "sku product_name family launch_date unit_cost_inr retail_price_inr warranty_months".split(), "dates": ["launch_date"]},
}


@dataclass(frozen=True)
class ColumnSchema:
    name: str
    dtype: str
    null_count: int
    null_rate: float
    unique_count: int
    likely_key: bool
    examples: list[str]
    parsing_issues: list[str]


def inspect_table(rows: list[dict[str, Any]]) -> list[ColumnSchema]:
    """Describe observed columns without assigning undocumented meanings."""
    if not rows:
        return []
    names = list(dict.fromkeys(name for row in rows for name in row))
    total = len(rows)
    result: list[ColumnSchema] = []
    for name in names:
        values = [row.get(name) for row in rows]
        present = [value for value in values if value not in (None, "")]
        unique = set(str(value) for value in present)
        # Infer a descriptive type while leaving actual CSV values untouched.
        parsed_int = bool(present) and all(_is_int(str(value)) for value in present)
        parsed_number = bool(present) and all(_is_number(str(value)) for value in present)
        date_like = any(token in name.lower() for token in ("date", "time", "timestamp"))
        date_valid = bool(present) and all(_is_date(str(value)) for value in present)
        dtype = "integer" if parsed_int else "number" if parsed_number else "date/time" if date_like and date_valid else "string"
        issues: list[str] = []
        if date_like:
            invalid_dates = sum(not _is_date(str(value)) for value in present)
            if invalid_dates:
                issues.append(f"{invalid_dates} non-empty values do not parse as dates/timestamps")
        elif any(token in name.lower() for token in ("count", "amount", "price", "quantity", "duration", "score")) and present:
            invalid_numbers = sum(not _is_number(str(value)) for value in present)
            if invalid_numbers:
                issues.append(f"{invalid_numbers} non-empty values do not parse as numbers")
        result.append(ColumnSchema(
            name=name,
            dtype=dtype,
            null_count=total - len(present),
            null_rate=(total - len(present)) / total,
            unique_count=len(unique),
            likely_key=(name.lower() == "id" or name.lower().endswith("_id")) and len(unique) == len(present) and bool(present),
            examples=[str(value) for value in list(dict.fromkeys(present))[:5]],
            parsing_issues=issues,
        ))
    return result


def schema_as_dicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [asdict(column) for column in inspect_table(rows)]


def _is_int(value: str) -> bool:
    try:
        int(value.strip())
        return True
    except ValueError:
        return False


def _is_number(value: str) -> bool:
    try:
        float(value.strip())
        return True
    except ValueError:
        return False


def _is_date(value: str) -> bool:
    candidate = value.strip()
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        return True
    except ValueError:
        pass
    try:
        date.fromisoformat(candidate)
        return True
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            datetime.strptime(candidate, fmt)
            return True
        except ValueError:
            continue
    return False
