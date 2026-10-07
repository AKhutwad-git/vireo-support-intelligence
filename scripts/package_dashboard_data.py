"""Create a minimal, data-reduced bundle for the dashboard container."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from vireo import __version__
from app.dashboard_data import REQUIRED_FIELDS, load_dashboard_data
from app.bundle_validation import sha256_file, validate_dashboard_bundle


TABLE_FIELDS = {
    "training_priority": sorted(REQUIRED_FIELDS["training_priority"] | {
        "agent_name", "agent_site", "agent_shift", "team", "tier", "peer_group", "priority_band", "diagnostic_state", "primary_signal", "secondary_signal",
        "csat_gap", "handle_time_gap", "sla_gap", "metric_directions", "economic_context", "ai_evidence_status",
        "training_theme", "roster_coverage", "priority_reason", "explanation", "limitations", "sample_size", "peer_agent_count",
        "review_score", "review_score_metric_count", "review_score_components", "review_score_status",
        "peer_mean_csat", "peer_handle_time_mean", "peer_sla_breach_rate"}),
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

OPTIONAL_ROOT_CAUSE_FIELDS = {
    "product_sku_analysis": ["product_sku", "product_name", "product_family", "ticket_count", "completed_ticket_count", "replacement_eligible_count", "replacement_count", "replacement_rate", "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status"],
    "product_family_analysis": ["product_family", "ticket_count", "completed_ticket_count", "replacement_eligible_count", "replacement_count", "replacement_rate", "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status"],
    "order_channel_analysis": ["order_channel", "ticket_count", "completed_ticket_count", "replacement_eligible_count", "replacement_count", "replacement_rate", "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status"],
    "product_lot_analysis": ["product_sku", "product_name", "product_family", "order_lot_code", "ticket_count", "completed_ticket_count", "replacement_eligible_count", "replacement_count", "replacement_rate", "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status"],
    "agent_product_exposure": ["agent_id", "product_sku", "product_name", "product_family", "ticket_count", "completed_ticket_count", "replacement_eligible_count", "replacement_count", "replacement_rate", "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status", "product_ticket_count", "share_of_product_tickets", "agent_ticket_count", "share_of_agent_tickets"],
}


def package_dashboard_data(source_dir: Path, output_dir: Path) -> dict:
    source_dir, output_dir = source_dir.resolve(), output_dir.resolve()
    if source_dir == output_dir or source_dir in output_dir.parents:
        raise ValueError("Dashboard bundle output must not be inside the source directory")
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite an existing bundle/candidate: {output_dir}")
    # Validate the same schemas/joins the app uses before producing a bundle.
    load_dashboard_data(ROOT, interim_dir=source_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent))
    try:
        tables = {}
        files = {}
        for name, columns in TABLE_FIELDS.items():
            source = source_dir / f"{name}.parquet"
            table = pq.read_table(source)
            missing = set(columns) - set(table.column_names)
            if missing:
                raise ValueError(f"{source.name} is missing deployment fields: {', '.join(sorted(missing))}")
            safe_table = table.select(columns)
            target = staging / source.name
            pq.write_table(safe_table, target, compression="zstd")
            tables[source.name] = safe_table.num_rows
            files[source.name] = {"purpose": f"Aggregate dashboard table: {name.replace('_', ' ')}",
                                  "format": "parquet", "schema_version": 1,
                                  "row_count": safe_table.num_rows, "columns": safe_table.column_names}

        root_cause_included = False
        for name, columns in OPTIONAL_ROOT_CAUSE_FIELDS.items():
            source = source_dir / f"{name}.parquet"
            if not source.is_file():
                continue
            table = pq.read_table(source)
            missing = set(columns) - set(table.column_names)
            if missing:
                raise ValueError(f"{source.name} is missing dashboard fields: {', '.join(sorted(missing))}")
            safe_table = table.select(columns)
            pq.write_table(safe_table, staging / source.name, compression="zstd")
            tables[source.name] = safe_table.num_rows
            files[source.name] = {"purpose": f"Aggregate product/order analysis: {name.replace('_', ' ')}",
                                  "format": "parquet", "schema_version": 1,
                                  "row_count": safe_table.num_rows, "columns": safe_table.column_names}
            root_cause_included = True
        root_summary = source_dir / "product_order_root_cause_summary.json"
        if root_cause_included and root_summary.is_file():
            shutil.copyfile(root_summary, staging / root_summary.name)
            files[root_summary.name] = {"purpose": "Product/order root-cause aggregate summary", "format": "json", "schema_version": 1}

        stage2 = json.loads((source_dir / "stage2_metrics_report.json").read_text(encoding="utf-8"))
        stage4 = json.loads((source_dir / "stage4_economics_report.json").read_text(encoding="utf-8"))
        stage2_summary = {"status": stage2.get("status"), "overall_metrics": stage2["overall_metrics"]}
        stage4_summary = {key: stage4[key] for key in ("status", "exposure_totals_inr", "available_quarters", "latest_complete_quarter")}
        (staging / "stage2_dashboard_summary.json").write_text(json.dumps(stage2_summary, indent=2) + "\n", encoding="utf-8")
        (staging / "stage4_dashboard_summary.json").write_text(json.dumps(stage4_summary, indent=2) + "\n", encoding="utf-8")
        files["stage2_dashboard_summary.json"] = {"purpose": "Stage 2 aggregate metric summary", "format": "json", "schema_version": 1}
        files["stage4_dashboard_summary.json"] = {"purpose": "Stage 4 aggregate economics summary", "format": "json", "schema_version": 1}

        stage6_summary_path = source_dir / "stage6_dashboard_summary.json"
        if not stage6_summary_path.is_file():
            raise FileNotFoundError("Stage 6 dashboard summary is required for review lists, budget, and business goal")
        shutil.copyfile(stage6_summary_path, staging / stage6_summary_path.name)
        files[stage6_summary_path.name] = {"purpose": "Stage 6 review queues, budget decision, and operational goal", "format": "json", "schema_version": 1}

        ai_report_path = source_dir / "ai_run_report.json"
        if ai_report_path.exists():
            ai_report = json.loads(ai_report_path.read_text(encoding="utf-8"))
            ai_summary = {"ai_status": ai_report.get("ai_status", "not_configured_or_unavailable"),
                          "tickets_analyzed": int(ai_report.get("tickets_analyzed", 0)),
                          "provider_requests_attempted": int(ai_report.get("provider_requests_attempted", 0))}
            (staging / "ai_dashboard_status.json").write_text(json.dumps(ai_summary, indent=2) + "\n", encoding="utf-8")
            files["ai_dashboard_status.json"] = {"purpose": "Optional Stage 5 provider and analysis status", "format": "json", "schema_version": 1}
        for name in ("ai_agent_diagnostics.parquet", "stage7_validation_report.json"):
            source = source_dir / name
            if source.exists():
                if source.suffix == ".parquet":
                    # AI output contains only aggregate themes and cited IDs, never source text.
                    table = pq.read_table(source)
                    pq.write_table(table, staging / name, compression="zstd")
                    files[name] = {"purpose": "Optional aggregate AI diagnostic themes and evidence", "format": "parquet",
                                   "schema_version": 1, "row_count": table.num_rows, "columns": table.column_names}
                else:
                    (staging / name).write_bytes(source.read_bytes())
                    files[name] = {"purpose": "Optional Stage 7 evaluation summary", "format": "json", "schema_version": 1}

        raw_root = ROOT / "data" / "raw"
        source_files = {}
        if raw_root.is_dir():
            for source in sorted(path for path in raw_root.rglob("*") if path.is_file()):
                relative = source.relative_to(raw_root).as_posix()
                source_files[relative] = {"sha256": sha256_file(source), "size_bytes": source.stat().st_size}
        snapshot = hashlib.sha256(json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        config_path = ROOT / "configs" / "config.yaml"
        try:
            revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
            dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip())
        except (OSError, subprocess.CalledProcessError):
            revision, dirty = None, None
        provenance = {"source_snapshot_sha256": snapshot, "source_files": source_files,
                      "pipeline_version": __version__, "pipeline_revision": revision,
                      "pipeline_worktree_dirty": dirty,
                      "decision_config_sha256": sha256_file(config_path),
                      "source_reporting_period": stage4_summary.get("available_quarters", []),
                      "bundle_created_at_utc": datetime.now(timezone.utc).isoformat()}

        for name, metadata in files.items():
            path = staging / name
            metadata["size_bytes"] = path.stat().st_size
            metadata["sha256"] = sha256_file(path)
        manifest = {"bundle_version": 1, "application_version": __version__,
                    "contains_raw_source_data": False, "table_row_counts": tables,
                    "files": files, "provenance": provenance,
                    "optional_ai_outputs_included": (staging / "ai_agent_diagnostics.parquet").exists(),
                    "product_order_analysis_included": root_cause_included,
                    "stage7_validation_included": (staging / "stage7_validation_report.json").exists()}
        (staging / "deployment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        validate_dashboard_bundle(staging)
        staging.rename(output_dir)
        return manifest
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data" / "interim")
    default_candidate = ROOT / "data" / "candidates" / datetime.now(timezone.utc).strftime("dashboard-%Y%m%dT%H%M%SZ")
    parser.add_argument("--output-dir", type=Path, default=default_candidate)
    args = parser.parse_args()
    try:
        manifest = package_dashboard_data(args.source_dir, args.output_dir)
    except Exception as exc:
        parser.exit(1, f"Dashboard data packaging failed: {exc}\n")
    print(f"Validated dashboard candidate ready: {len(manifest['table_row_counts'])} tables; raw source data excluded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
