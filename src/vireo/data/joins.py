"""Validated joins. No relationship is presumed by this module."""

from __future__ import annotations

from typing import Any

from .validators import validate_relationship


def validated_left_join(fact_rows: list[dict[str, Any]], dimension_rows: list[dict[str, Any]], fact_foreign_key: str, dimension_key: str, *, prefix: str = "") -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Join a validated many-to-one dimension onto fact rows without changing fact count."""
    dimension_values = [row.get(dimension_key) for row in dimension_rows]
    if len(dimension_values) != len(set(dimension_values)):
        raise ValueError("Join rejected: dimension key is not unique")
    checks = validate_relationship("dimension", "fact", dimension_rows, fact_rows, dimension_key, fact_foreign_key)
    if any(check.status == "FAIL" for check in checks):
        raise ValueError("Join rejected: relationship validation failed")
    lookup = {row.get(dimension_key): row for row in dimension_rows}
    joined: list[dict[str, Any]] = []
    for row in fact_rows:
        related = lookup.get(row.get(fact_foreign_key), {})
        joined.append({**row, **{f"{prefix}{key}": value for key, value in related.items() if key != dimension_key and key not in row}})
    if len(joined) != len(fact_rows):
        raise ValueError("Join rejected: unexpected row-count change")
    return joined, checks
