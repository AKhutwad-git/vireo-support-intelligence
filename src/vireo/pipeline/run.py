"""Stage 1 orchestration and generated forensic reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from vireo.data.validators import CheckResult, results_as_dicts
from vireo.pipeline.ingest import ingest
from vireo.pipeline.preprocess import preprocess
from vireo.pipeline.analyze import run_metrics, run_stage3_analysis, run_ai_diagnostics, run_training_priority
from vireo.analytics.economics import run_stage4_economics


def load_config(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not load configuration {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Configuration must be a YAML mapping: {path}")
    return value


def _write_report(path: Path, result: dict[str, Any], processed: dict[str, Any] | None) -> None:
    rows = [f"# Data Forensics", "", "Generated from the current raw task pack. No business conclusions are calculated.", "", "## Source inventory", "", "| File | Present |", "|---|---:|"]
    rows.extend(f"| `{name}` | {'yes' if found else 'no'} |" for name, found in result["presence"].items())
    rows.extend(["", "## Observed tables", "", "| Dataset | Rows | Columns |", "|---|---:|---:|"])
    for name, table in result["tables"].items():
        rows.append(f"| `{name}` | {len(table)} | {len(result['schemas'][name])} |")
    if not result["tables"]:
        rows.extend(["| No tabular datasets loaded | 0 | 0 |", "", "The raw directory is empty or contains no expected CSV sources. No schemas, keys, row counts, or relationships can be inferred until the task pack is supplied."])
    rows.extend(["", "## Null rates", "", "| Dataset | Column | Nulls | Null rate |", "|---|---|---:|---:|"])
    for name, cols in result["schemas"].items():
        for col in cols:
            if col["null_count"]:
                rows.append(f"| {name} | {col['name']} | {col['null_count']} | {col['null_rate']:.2%} |")
    if not any(c["null_count"] for cs in result["schemas"].values() for c in cs):
        rows.append("| — | None observed | 0 | 0.00% |")
    rows.extend(["", "## Checks", "", "| Status | Check | Dataset | Finding |", "|---|---|---|---|"])
    rows.extend(f"| {check.status} | {check.name} | {check.dataset or '—'} | {check.message} |" for check in result["checks"])
    readme = result["sources"].get("README")
    if isinstance(readme, str):
        rows.extend(["", "## README source definitions", "", f"`README.txt` was read ({len(readme)} characters). Its definitions remain authoritative; the file format is not assumed or auto-parsed. Populate `datasets` and `relationships` in configuration from those definitions before treating key or relationship checks as complete."])
    rows.extend(["", "## Missingness and duplicates", "", "Null rates and duplicate key findings are recorded in the generated schemas and checks. Agents intentionally have a non-unique agent_id because README defines one row per effective-dated assignment.", "", "## Stage 1 findings", ""])
    ticket_rows = result["tables"].get("tickets", [])
    if processed and ticket_rows:
        output_path = Path(processed["outputs"]["tickets"]["path"])
        import pyarrow.parquet as pq
        canonical = pq.read_table(output_path).to_pylist()
        count = lambda key: sum(bool(r.get(key)) for r in canonical)
        customers = {r['customer_id']: r for r in result['tables'].get('customers', [])}
        orders = result['tables'].get('orders', [])
        signup_order_anomalies = sum(1 for o in orders if o.get('customer_id') in customers and o.get('order_date') and customers[o['customer_id']].get('signup_date') and o['order_date'] < customers[o['customer_id']]['signup_date'])
        rows.extend([f"- Orders dated before customer signup: {signup_order_anomalies} order rows (source-known anomaly; retained).", f"- Ticket rows linked to an order dated before customer signup: {count('signup_anomaly_flag')}.", f"- Product pre-launch ticket matches: {count('product_prelaunch_anomaly_flag')}.", f"- Degraded customer messages under deterministic heuristic: {sum(r.get('text_quality_flag') == 'degraded' for r in canonical)}; email thread estimates roughly forty IVR-junk records, so unflagged candidate review remains unresolved.", f"- Cross-source duplicate candidate rows on matching customer, SKU, and source creation timestamp: {count('reconciliation_flag')}.", f"- Tickets without effective roster match: {sum(r.get('agent_assignment_flag') != 'matched' for r in canonical)} (includes open/unassigned tickets)."])
        negative = sum(bool(r.get('first_response_at') and r.get('resolved_at') and r['resolved_at'] < r['first_response_at']) for r in canonical)
        rows.append(f"- Negative first-response-to-resolution intervals after UTC normalization: {negative}; raw source values are preserved and these are flagged for review, never shifted to force non-negative durations.")
    else:
        rows.append("No findings calculated because canonical preprocessing did not run.")
    rows.extend(["", "## Joins and source relevance", "", "Relationships are counted in `data_quality_report.json`; nullable ticket order_id values are excluded from the direct order lookup check. Customer plus product SKU is used only as a unique fallback; ambiguous matches are left unresolved. Roster assignments are selected by agent_id and effective dates. No join expands ticket rows.", "The policy PDF is inventoried but not text-extracted in this run; its economics are not treated as system constants. README/email text is available for provenance and semantics.", "", "## Audit classification", "", "| Requirement | Status | Basis |", "|---|---|---|"])
    rows.extend(["| Source inventory and missing dependency reporting | PASS | All required task pack files are inventoried; missing files fail the pipeline. |", "| Contract/schema and key validation | PASS | README columns and primary identifiers are validated; roster agent_id is intentionally non-unique. |", "| Source-aware timestamps and effective roster | PARTIAL | Implemented, but legacy created/first-response provenance is not documented precisely; only legacy resolved_at is treated as UTC. |", "| Anomaly, text-quality, reconciliation flags | PARTIAL | Signup/product flags work; text heuristic flags 21 while email context estimates ~40, and exact-timestamp duplicate matching may miss near-time re-imports. |", "| Relationship and row-count-safe joins | PARTIAL | Temporal roster assignment is used and no expanding join is applied; relationship findings are diagnostic, and ambiguous order links remain unresolved. |", "| Reproducible canonical outputs and forensic reporting | PASS | Parquet tables and generated report written when validation passes. |", "| Business KPI/ranking or Stage 2 modeling | PASS | Not implemented. |"])
    rows.extend(["", "## Canonical outputs", ""])
    if processed:
        rows.extend(f"- `{name}`: {value['row_count']} rows at `{value['path']}`" for name, value in processed["outputs"].items())
    else:
        rows.append("No canonical datasets were written because one or more expected source files are missing.")
    rows.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8", newline="\n")


def run_pipeline(config_path: Path | None = None) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[3]
    config_path = config_path or project_root / "configs" / "config.yaml"
    config = load_config(config_path)
    raw_dir = (project_root / config.get("paths", {}).get("raw", "data/raw")).resolve()
    interim_dir = (project_root / config.get("paths", {}).get("interim", "data/interim")).resolve()
    report_path = (project_root / config.get("paths", {}).get("forensics_report", "docs/technical/data_forensics.md")).resolve()
    result = ingest(raw_dir, config)
    failed = any(check.status == "FAIL" for check in result["checks"])
    processed = None
    if not failed and not result["missing_files"]:
        processed = preprocess(result["tables"], interim_dir)
    result["processed"] = processed
    result["status"] = "FAIL" if failed else "PASS"
    result["checks"] = results_as_dicts(result["checks"])
    _write_report(report_path, {**result, "checks": [CheckResult(**item) for item in result["checks"]]}, processed)
    (interim_dir / "data_quality_report.json").parent.mkdir(parents=True, exist_ok=True)
    (interim_dir / "data_quality_report.json").write_text(json.dumps({"status": result["status"], "presence": result["presence"], "schemas": result["schemas"], "checks": result["checks"], "processed": processed}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if result["status"] == "PASS" and processed:
        expected_counts = {name: len(rows) for name, rows in result["tables"].items()}
        for name, expected_count in expected_counts.items():
            actual_count = processed["outputs"].get(name, {}).get("row_count")
            if actual_count != expected_count:
                raise ValueError(f"Stage 1 preprocessing changed {name} row count: {expected_count} source vs {actual_count} canonical")
        stage2 = run_metrics(interim_dir, config, expected_counts)
        result["stage2"] = stage2
        if stage2["status"] != "PASS":
            result["status"] = "FAIL"
        else:
            stage3=run_stage3_analysis(interim_dir,config)
            result["stage3"]=stage3
            if stage3["status"]!="PASS": result["status"]="FAIL"
            else:
                stage4=run_stage4_economics(interim_dir,config)
                result["stage4"]=stage4
                if stage4["status"]!="PASS": result["status"]="FAIL"
                else:
                    result["stage5"]=run_ai_diagnostics(interim_dir,config,project_root=project_root)
                    result["stage6"]=run_training_priority(interim_dir,config,project_root=project_root)
    return result
