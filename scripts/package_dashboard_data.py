"""Create a minimal, PII-reduced bundle for the dashboard container."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from vireo import __version__
from app.dashboard_data import REQUIRED_FIELDS, load_dashboard_data


TABLE_FIELDS = {
    "training_priority": sorted(REQUIRED_FIELDS["training_priority"] | {
        "team", "tier", "peer_group", "priority_band", "diagnostic_state", "primary_signal", "secondary_signal",
        "csat_gap", "handle_time_gap", "sla_gap", "metric_directions", "economic_context", "ai_evidence_status",
        "training_theme", "roster_coverage", "priority_reason", "explanation", "limitations", "sample_size", "peer_agent_count"}),
    "agent_comparison": sorted(REQUIRED_FIELDS["agent_comparison"] | {
        "agent_from_date", "agent_to_date", "peer_fallback_level", "peer_agent_count", "peer_supported", "period", "ticket_count",
        "csat_eligible_count", "csat_evidence_strength", "csat_gap_ci_lower", "csat_gap_ci_upper", "csat_gap_interval_direction",
        "handle_time_eligible_count", "handle_time_evidence_strength", "handle_time_gap_ci_lower", "handle_time_gap_ci_upper",
        "handle_time_gap_interval_direction", "sla_eligible_count", "sla_evidence_strength", "sla_gap_ci_lower", "sla_gap_ci_upper",
        "sla_gap_interval_direction", "stability_flag", "comparison_status"}),
    "agent_economics": sorted(REQUIRED_FIELDS["agent_economics"] | {
        "agent_team", "agent_tier", "agent_site", "agent_shift", "ticket_count", "completed_ticket_count",
        "internal_transfer_cost_exposure_inr"}),
    "agent_metrics": sorted(REQUIRED_FIELDS["agent_metrics"]),
}


def package_dashboard_data(source_dir: Path, output_dir: Path) -> dict:
    source_dir, output_dir = source_dir.resolve(), output_dir.resolve()
    if source_dir == output_dir or source_dir in output_dir.parents:
        raise ValueError("Dashboard bundle output must not be inside the source directory")
    # Validate the same schemas/joins the app uses before producing a bundle.
    load_dashboard_data(ROOT, interim_dir=source_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tables = {}
    files = {}
    for name, columns in TABLE_FIELDS.items():
        source = source_dir / f"{name}.parquet"
        table = pq.read_table(source)
        missing = set(columns) - set(table.column_names)
        if missing:
            raise ValueError(f"{source.name} is missing deployment fields: {', '.join(sorted(missing))}")
        safe_table = table.select(columns)
        target = output_dir / source.name
        pq.write_table(safe_table, target, compression="zstd")
        tables[source.name] = safe_table.num_rows
        files[source.name] = {
            "purpose": f"Aggregate dashboard table: {name.replace('_', ' ')}",
            "format": "parquet",
            "schema_version": 1,
            "row_count": safe_table.num_rows,
            "columns": safe_table.column_names,
        }

    stage2 = json.loads((source_dir / "stage2_metrics_report.json").read_text(encoding="utf-8"))
    stage4 = json.loads((source_dir / "stage4_economics_report.json").read_text(encoding="utf-8"))
    stage2_summary = {"status": stage2.get("status"), "overall_metrics": stage2["overall_metrics"]}
    stage4_summary = {key: stage4[key] for key in ("status", "exposure_totals_inr", "available_quarters", "latest_complete_quarter")}
    (output_dir / "stage2_dashboard_summary.json").write_text(json.dumps(stage2_summary, indent=2) + "\n", encoding="utf-8")
    (output_dir / "stage4_dashboard_summary.json").write_text(json.dumps(stage4_summary, indent=2) + "\n", encoding="utf-8")
    files["stage2_dashboard_summary.json"] = {"purpose": "Stage 2 aggregate metric summary", "format": "json", "schema_version": 1}
    files["stage4_dashboard_summary.json"] = {"purpose": "Stage 4 aggregate economics summary", "format": "json", "schema_version": 1}

    ai_report_path = source_dir / "ai_run_report.json"
    if ai_report_path.exists():
        ai_report = json.loads(ai_report_path.read_text(encoding="utf-8"))
        ai_summary = {"ai_status": ai_report.get("ai_status", "not_configured_or_unavailable"),
                      "tickets_analyzed": int(ai_report.get("tickets_analyzed", 0)),
                      "provider_requests_attempted": int(ai_report.get("provider_requests_attempted", 0))}
        (output_dir / "ai_dashboard_status.json").write_text(json.dumps(ai_summary, indent=2) + "\n", encoding="utf-8")
        files["ai_dashboard_status.json"] = {"purpose": "Optional Stage 5 provider and analysis status", "format": "json", "schema_version": 1}
    for name in ("ai_agent_diagnostics.parquet", "stage7_validation_report.json"):
        source = source_dir / name
        if source.exists():
            if source.suffix == ".parquet":
                # AI output contains only aggregate themes and cited IDs, never source text.
                table = pq.read_table(source)
                pq.write_table(table, output_dir / name, compression="zstd")
                files[name] = {"purpose": "Optional aggregate AI diagnostic themes and evidence", "format": "parquet",
                               "schema_version": 1, "row_count": table.num_rows, "columns": table.column_names}
            else:
                (output_dir / name).write_bytes(source.read_bytes())
                files[name] = {"purpose": "Optional Stage 7 evaluation summary", "format": "json", "schema_version": 1}

    manifest = {"bundle_version": 1, "application_version": __version__,
                "contains_raw_source_data": False, "table_row_counts": tables,
                "files": files,
                "optional_ai_outputs_included": (output_dir / "ai_agent_diagnostics.parquet").exists(),
                "stage7_validation_included": (output_dir / "stage7_validation_report.json").exists()}
    (output_dir / "deployment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data" / "interim")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "deployment")
    args = parser.parse_args()
    try:
        manifest = package_dashboard_data(args.source_dir, args.output_dir)
    except Exception as exc:
        parser.exit(1, f"Dashboard data packaging failed: {exc}\n")
    print(f"Dashboard bundle ready: {len(manifest['table_row_counts'])} tables; raw source data excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
