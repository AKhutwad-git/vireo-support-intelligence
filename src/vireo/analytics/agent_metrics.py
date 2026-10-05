"""Agent-ID and effective-assignment summaries from ticket-level metrics."""
from __future__ import annotations
from collections import defaultdict
from typing import Any
from .aggregate import summarize

def _groups(rows, keys):
    result = defaultdict(list)
    for row in rows:
        result[tuple(row.get(k) for k in keys)].append(row)
    return result

def agent_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = ["agent_id"]
    return [{**dict(zip(keys, key)), **summarize(group)} for key, group in sorted(_groups(rows, keys).items(), key=lambda x: str(x[0]))]

def agent_assignment_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = ["agent_id", "agent_assignment_flag", "agent_team", "agent_tier", "agent_site", "agent_shift", "agent_from_date", "agent_to_date"]
    output = [{**dict(zip(keys, key)), "period_type": "full_available_period", "period": "all", "reporting_month": None, **summarize(group)}
              for key, group in sorted(_groups(rows, keys).items(), key=lambda x: str(x[0]))]
    monthly_keys = keys + ["reporting_month"]
    output.extend({**dict(zip(monthly_keys, key)), "period_type": "month", "period": key[-1], **summarize(group)}
                  for key, group in sorted(_groups([r for r in rows if r.get("reporting_month")], monthly_keys).items(), key=lambda x: str(x[0])))
    return output
