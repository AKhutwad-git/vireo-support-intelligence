"""Flag likely cross-source duplicate ticket records without dropping any rows."""
from __future__ import annotations
from collections import defaultdict
from typing import Any

def flag_duplicate_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for i, row in enumerate(rows):
        key = tuple(str(row.get(k) or "").strip().casefold() for k in ("customer_id", "product_sku", "created_at"))
        if all(key):
            groups[key].append(i)
    flagged: set[int] = set()
    for indices in groups.values():
        sources = {rows[i].get("source_system") for i in indices}
        if len(sources) > 1:
            flagged.update(indices)
    return [{**row, "reconciliation_flag": i in flagged,
             "reconciliation_reason": "cross_source_same_customer_product_created_at" if i in flagged else ""}
            for i, row in enumerate(rows)]
