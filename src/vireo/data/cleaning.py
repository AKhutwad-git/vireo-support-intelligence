"""Meaning-preserving, traceable text normalization for raw CSV values."""

from __future__ import annotations

from typing import Any


MISSING_TOKENS = {"", "na", "n/a", "null", "none"}


def normalize_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = " ".join(value.split())
    if normalized.casefold() in MISSING_TOKENS:
        return ""
    return normalized


def normalize_table(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return normalized copy and per-cell change log; never discard records."""
    normalized: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows, start=1):
        clean: dict[str, Any] = {}
        for column, before in row.items():
            after = normalize_value(before)
            clean[column] = after
            if after != before:
                changes.append({"row": row_index, "column": column, "before": before, "after": after})
        normalized.append(clean)
    return normalized, changes
