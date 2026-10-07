"""Validated, presentation-ready views over generated pipeline artifacts."""
from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path

import pyarrow.parquet as pq

from vireo.scoring.review import build_review_lists


REQUIRED_FIELDS = {
    "training_priority": {"agent_id", "agent_name", "agent_site", "agent_shift", "peer_supported", "comparison_status",
        "review_score", "review_score_metric_count", "review_score_components", "review_score_status",
        "peer_mean_csat", "peer_handle_time_mean", "peer_sla_breach_rate",
        "priority_status", "priority_score", "priority_rank", "priority_reason", "evidence_strength", "stability", "uncertainty", "representative_ticket_ids"},
    "agent_comparison": {"agent_id", "period_type", "agent_team", "agent_tier", "agent_site", "agent_shift", "comparison_group", "raw_mean_csat", "peer_mean_csat", "csat_gap", "raw_handle_time_mean", "peer_handle_time_mean", "handle_time_gap", "raw_sla_breach_rate", "peer_sla_breach_rate", "sla_gap"},
    "agent_economics": {"agent_id", "total_relevant_exposure_inr", "operational_cost_exposure_inr", "replacement_exposure_inr", "refund_exposure_inr"},
    "agent_metrics": {"agent_id", "ticket_count", "completed_ticket_count", "csat_completed_response_count", "csat_response_rate", "mean_csat", "handle_time_median", "sla_breach_count", "sla_eligible_count", "sla_breach_rate", "total_transfers"},
}


def _read_parquet(path: Path, required_fields: set[str] | None = None) -> list[dict]:
    table = pq.read_table(path)
    missing = (required_fields or set()) - set(table.column_names)
    if missing:
        raise ValueError(f"{path.name} is missing required fields: {', '.join(sorted(missing))}")
    return table.to_pylist()


def resolve_interim_dir(project_root: str | Path, interim_dir: str | Path | None = None) -> Path:
    """Resolve the generated dashboard bundle independently of process CWD."""
    root = Path(project_root).resolve()
    configured = interim_dir if interim_dir is not None else os.environ.get("VIREO_INTERIM_DIR")
    path = Path(configured).expanduser() if configured else root / "data" / "interim"
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def filter_value(value) -> str:
    """Give missing categorical values an explicit, selectable filter bucket."""
    return "Unavailable" if value is None else str(value)


def filter_agent_rows(rows: list[dict], selections: dict[str, set[str]], query: str = "") -> list[dict]:
    filtered = [row for row in rows if all(filter_value(row.get(field)) in selected
                                            for field, selected in selections.items())]
    if query.strip():
        filtered = [row for row in filtered if query.strip().lower() in str(row.get("agent_id", "")).lower()]
    return filtered


def load_dashboard_data(project_root: str | Path, interim_dir: str | Path | None = None) -> dict:
    """Load and validate current generated outputs; AI diagnostics are optional."""
    root = Path(project_root).resolve()
    interim = resolve_interim_dir(root, interim_dir)
    tables = {name: _read_parquet(interim / f"{name}.parquet", fields)
              for name, fields in REQUIRED_FIELDS.items()}
    comparison = [r for r in tables["agent_comparison"] if r.get("period_type") == "full_available_period"]
    if not comparison:
        raise ValueError("agent_comparison.parquet has no full_available_period rows")
    by_id = {r["agent_id"]: r for r in comparison}
    for name in ("training_priority", "agent_economics", "agent_metrics"):
        ids = {r["agent_id"] for r in tables[name]}
        if ids != set(by_id):
            raise ValueError(f"{name}.parquet agent IDs do not match full-period comparison IDs")

    priority = {r["agent_id"]: r for r in tables["training_priority"]}
    economics = {r["agent_id"]: r for r in tables["agent_economics"]}
    metrics = {r["agent_id"]: r for r in tables["agent_metrics"]}
    agents = []
    for agent_id, compare in by_id.items():
        row = {**compare, **metrics[agent_id], **economics[agent_id], **priority[agent_id]}
        row["agent_id"] = agent_id
        agents.append(row)
    agents.sort(key=lambda r: r["agent_id"])

    ai_path = interim / "ai_agent_diagnostics.parquet"
    ai_rows = _read_parquet(ai_path) if ai_path.exists() else []
    ai_by_id = {r["agent_id"]: r for r in ai_rows if r.get("agent_id")}
    for row in agents:
        row["ai_diagnostics"] = ai_by_id.get(row["agent_id"])

    stage2_path = interim / "stage2_dashboard_summary.json"
    if not stage2_path.exists():
        stage2_path = interim / "stage2_metrics_report.json"
    stage2 = json.loads(stage2_path.read_text(encoding="utf-8"))
    stage4_path = interim / "stage4_dashboard_summary.json"
    if not stage4_path.exists():
        stage4_path = interim / "stage4_economics_report.json"
    stage4 = json.loads(stage4_path.read_text(encoding="utf-8"))
    stage7_path = interim / "stage7_validation_report.json"
    stage7 = json.loads(stage7_path.read_text(encoding="utf-8")) if stage7_path.exists() else None
    ai_path_report = interim / "ai_dashboard_status.json"
    if not ai_path_report.exists():
        ai_path_report = interim / "ai_run_report.json"
    ai_report = json.loads(ai_path_report.read_text(encoding="utf-8")) if ai_path_report.exists() else {}
    stage6_path = interim / "stage6_dashboard_summary.json"
    stage6 = json.loads(stage6_path.read_text(encoding="utf-8")) if stage6_path.exists() else {}
    root_cause = {}
    for key, filename in (("product_sku", "product_sku_analysis.parquet"),
                          ("product_family", "product_family_analysis.parquet"),
                          ("order_channel", "order_channel_analysis.parquet"),
                          ("lot", "product_lot_analysis.parquet"),
                          ("agent_product", "agent_product_exposure.parquet")):
        path = interim / filename
        root_cause[key] = _read_parquet(path) if path.is_file() else []
    root_cause_summary_path = interim / "product_order_root_cause_summary.json"
    root_cause["summary"] = json.loads(root_cause_summary_path.read_text(encoding="utf-8")) if root_cause_summary_path.is_file() else None
    quarters = stage4.get("available_quarters") or stage4.get("quarters") or []
    if not quarters and (interim / "ticket_metrics.parquet").exists():
        quarters = sorted({r.get("reporting_quarter") for r in _read_parquet(interim / "ticket_metrics.parquet") if r.get("reporting_quarter")})
    overall = stage2.get("overall_metrics", stage2)
    exposure = stage4["exposure_totals_inr"]
    priority_counts = {}
    for row in agents:
        status = row.get("priority_status", "unknown")
        priority_counts[status] = priority_counts.get(status, 0) + 1
    review_lists = build_review_lists(agents)
    return {"agents": agents, "overall": overall, "exposure": exposure,
            "latest_quarter": stage4.get("latest_complete_quarter") or (quarters[-1] if quarters else "Unavailable"),
            "available_period": (quarters[0], quarters[-1]) if quarters else ("Unavailable", "Unavailable"),
            "priority_counts": priority_counts, "stage7": stage7, "ai_report": ai_report,
            "ai_by_agent": ai_by_id, "stage6": stage6, "review_lists": review_lists,
            "root_cause": root_cause, "interim": interim}


EXPORT_COLUMNS = {
    "training_priority": ["agent_id", "team", "tier", "peer_group", "priority_status", "priority_band", "priority_rank", "priority_score", "evidence_strength", "stability", "uncertainty", "priority_reason", "representative_ticket_ids"],
    "agent_performance": ["agent_id", "agent_team", "agent_tier", "agent_site", "agent_shift", "comparison_group", "ticket_count", "completed_ticket_count", "csat_completed_response_count", "csat_response_rate", "raw_mean_csat", "peer_mean_csat", "csat_gap", "handle_time_median", "raw_handle_time_mean", "peer_handle_time_mean", "handle_time_gap", "sla_breach_rate", "peer_sla_breach_rate", "sla_gap", "evidence_strength", "stability", "priority_status"],
    "agent_economics": ["agent_id", "agent_team", "agent_tier", "ticket_count", "completed_ticket_count", "operational_cost_exposure_inr", "internal_transfer_cost_exposure_inr", "replacement_exposure_inr", "refund_exposure_inr", "total_relevant_exposure_inr"],
}


def export_csv(rows: list[dict], export_name: str) -> bytes:
    """Export an explicitly selected field set without an index or recomputed rank."""
    columns = EXPORT_COLUMNS[export_name]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), (list, dict)) else row.get(key)
                         for key in columns})
    return output.getvalue().encode("utf-8-sig")


def stage7_summary_json(stage7: dict | None) -> bytes:
    return (json.dumps(stage7 or {"status": "unavailable"}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
