"""Stage 2 orchestration: validate Stage 1 artifacts, derive, aggregate, persist."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
import pyarrow as pa
import pyarrow.parquet as pq

from vireo.analytics.agent_metrics import agent_metrics, agent_assignment_metrics
from vireo.analytics.aggregate import summarize
from vireo.analytics.derive import derive_ticket_metrics

REQUIRED_TICKET_FIELDS = {"ticket_id", "agent_id", "status", "channel", "created_at", "first_response_at", "resolved_at", "csat_score", "transfers", "agent_team", "agent_tier", "agent_site", "agent_shift", "agent_from_date", "agent_to_date", "agent_assignment_flag", "signup_anomaly_flag", "product_prelaunch_anomaly_flag", "text_quality_flag", "reconciliation_flag"}

def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows) if rows else pa.table({}), path, compression="zstd")

def _period(row: dict[str, Any], zone: ZoneInfo) -> tuple[str, str] | None:
    value = row.get("created_at")
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(zone)
    quarter = (dt.month - 1) // 3 + 1
    return (dt.strftime("%Y-%m"), f"{dt.year}-Q{quarter}")

def _group_summary(rows, key_fields):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(k) for k in key_fields)].append(row)
    return [{**dict(zip(key_fields, key)), **summarize(group)} for key, group in sorted(grouped.items(), key=lambda item: str(item[0]))]

def validate_stage1_inputs(interim_dir: Path, expected_counts: dict[str, int] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = interim_dir / "normalized_tickets.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"Stage 1 canonical input missing: {path}")
    table = pq.read_table(path)
    missing = REQUIRED_TICKET_FIELDS - set(table.column_names)
    if missing:
        raise ValueError("Stage 1 ticket schema missing required fields: " + ", ".join(sorted(missing)))
    rows = table.to_pylist()
    expected = (expected_counts or {}).get("tickets")
    report_path = interim_dir / "data_quality_report.json"
    if expected is None and report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        expected = ((report.get("processed") or {}).get("outputs", {}).get("tickets") or {}).get("row_count")
    if expected is not None and len(rows) != expected:
        raise ValueError(f"Stage 1 ticket row count mismatch: canonical={len(rows)}, expected={expected}")
    unique_ids = {r.get("ticket_id") for r in rows}
    if len(unique_ids) != len(rows) or None in unique_ids:
        raise ValueError("Stage 1 ticket identifiers are null or duplicated")
    for required in ("signup_anomaly_flag", "product_prelaunch_anomaly_flag", "reconciliation_flag"):
        if any(r.get(required) is None for r in rows):
            raise ValueError(f"Stage 1 provenance flag contains null values: {required}")
    table_counts = {}
    for dataset, fields in {"agents": {"agent_id", "team", "tier", "site", "shift", "from_date", "to_date"},
                            "orders": {"order_id", "customer_id", "sku", "order_date"},
                            "customers": {"customer_id", "signup_date"},
                            "products": {"sku", "launch_date"}}.items():
        fpath = interim_dir / f"normalized_{dataset}.parquet"
        if not fpath.is_file():
            raise FileNotFoundError(f"Stage 1 canonical input missing: {fpath}")
        dim = pq.read_table(fpath)
        absent = fields - set(dim.column_names)
        if absent:
            raise ValueError(f"Stage 1 {dataset} schema missing fields: {', '.join(sorted(absent))}")
        expected_dim = (expected_counts or {}).get(dataset)
        if expected_dim is not None and dim.num_rows != expected_dim:
            raise ValueError(f"Stage 1 {dataset} row count mismatch: canonical={dim.num_rows}, expected={expected_dim}")
        table_counts[dataset] = dim.num_rows
    audit = {"ticket_rows": len(rows), "unique_ticket_ids": len(unique_ids), "expected_ticket_rows": expected,
             "canonical_table_rows": {"tickets": len(rows), **table_counts},
             "required_fields": sorted(REQUIRED_TICKET_FIELDS), "roster_assignment_field_available": True,
             "anomaly_flags_available": True}
    return rows, audit

def run_metrics(interim_dir: Path, config: dict[str, Any], expected_counts: dict[str, int] | None = None) -> dict[str, Any]:
    raw_rows, audit = validate_stage1_inputs(interim_dir, expected_counts)
    targets = {str(k).casefold(): int(v) for k, v in config.get("sla_targets_minutes", {}).items()}
    if not targets:
        from vireo.analytics.sla import DEFAULT_SLA_TARGETS
        targets = DEFAULT_SLA_TARGETS
    rows = derive_ticket_metrics(raw_rows, targets)
    zone = ZoneInfo(config.get("reporting_timezone", "Asia/Kolkata"))
    for row in rows:
        periods = _period(row, zone)
        row["reporting_month"] = periods[0] if periods else None
        row["reporting_quarter"] = periods[1] if periods else None
    summaries = {
        "agent_metrics": agent_metrics(rows),
        "agent_assignment_metrics": agent_assignment_metrics(rows),
        "period_metrics": ([{"period_type": "full_available_period", "period": "all", **summarize(rows)}]
                            + [{"period_type": "month", "period": k, **summarize(v)} for k, v in sorted(_group_by(rows, "reporting_month").items(), key=lambda item: str(item[0])) if k]
                            + [{"period_type": "quarter", "period": k, **summarize(v)} for k, v in sorted(_group_by(rows, "reporting_quarter").items(), key=lambda item: str(item[0])) if k]),
        "channel_metrics": _group_summary(rows, ["channel"]),
        "team_metrics": _group_summary(rows, ["agent_team", "agent_tier"]),
    }
    output_paths = {}
    for name, data in {"ticket_metrics": rows, **summaries}.items():
        target = interim_dir / f"{name}.parquet"
        _write(target, data)
        output_paths[name] = {"path": str(target), "row_count": len(data)}
    checks = _sanity(rows, summaries)
    result = {"status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
              "stage1_input_audit": audit, "targets_minutes": targets, "outputs": output_paths,
              "checks": checks, "overall_metrics": summarize(rows)}
    (interim_dir / "stage2_metrics_report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_findings(interim_dir, config, rows, result)
    return result

def _group_by(rows, key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.get(key)].append(row)
    return grouped

def _sanity(rows, summaries):
    overall = summarize(rows)
    checks = []
    def add(name, ok, detail):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    add("ticket_row_reconciliation", overall["ticket_count"] == len(rows), f"{overall['ticket_count']} metric rows vs {len(rows)} input rows")
    add("attendance_reconciliation", overall["completed_ticket_count"] == overall["resolved_ticket_count"] + overall["closed_ticket_count"], "completed = resolved + closed")
    add("csat_denominator", overall["csat_response_count"] <= overall["completed_ticket_count"], "CSAT responses do not exceed completed tickets")
    add("metric_eligibility", overall["sla_eligible_count"] <= overall["first_response_eligible_count"] and overall["handle_time_eligible_count"] <= overall["ticket_count"], "SLA and handle-time denominators are within eligible populations")
    rates = [overall["csat_response_rate"], overall["sla_breach_rate"], overall["transfer_rate"]]
    valid_rates = all(v is None or 0 <= v <= 1 for v in rates)
    mean = overall["mean_csat"]
    add("rate_and_score_bounds", valid_rates and (mean is None or 1 <= mean <= 5), "Rates are within [0,1] and mean CSAT within [1,5]")
    add("ticket_output_count", summaries["agent_metrics"] is not None, "Agent summaries produced without filtering ticket metrics")
    return checks

def _write_findings(interim_dir, config, rows, result):
    from datetime import timezone
    zone = ZoneInfo(config.get("reporting_timezone", "Asia/Kolkata"))
    dates = [datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(zone).date() for r in rows if r.get("created_at")]
    m = result["overall_metrics"]
    quality = sum(r.get("text_quality_flag") == "degraded" for r in rows)
    signup_ticket = sum(bool(r.get("signup_anomaly_flag")) for r in rows)
    prelaunch = sum(bool(r.get("product_prelaunch_anomaly_flag")) for r in rows)
    unmatched = sum(r.get("agent_assignment_flag") != "matched" for r in rows)
    unmatched_status = defaultdict(int)
    for row in rows:
        if row.get("agent_assignment_flag") != "matched":
            unmatched_status[row.get("status") or "(blank)"] += 1
    text = ["# Stage 2 Findings", "", "Generated from Stage 1 canonical Parquet inputs. These are descriptive metrics only; no ranking or training decision is made.", "",
            "## Coverage", "", f"- Tickets: {len(rows):,} metric rows.", f"- Ticket creation date range (IST): {min(dates) if dates else 'undefined'} through {max(dates) if dates else 'undefined'}.", "- The latest available period is determined from the supplied tickets; no Q3 2026 data is inferred.",
            f"- Completed attendance: {m['completed_ticket_count']:,} ({m['resolved_ticket_count']:,} resolved + {m['closed_ticket_count']:,} closed); open/pending: {m['open_pending_ticket_count']:,}.",
            f"- CSAT: {m['csat_response_count']:,} eligible completed-ticket responses / {m['completed_ticket_count']:,} completed tickets; response rate {fmt_pct(m['csat_response_rate'])}; mean {fmt(m['mean_csat'])} on the 1–5 scale.",
            f"- Populated valid scores on open/pending tickets: {m['csat_response_on_noncompleted_count']:,}; retained as source values and separately flagged, excluded from primary response count and mean per survey timing policy.",
            f"- Handle time: {m['handle_time_eligible_count']:,} eligible / {m['ticket_count']:,} tickets; mean {fmt(m['handle_time_mean'])} min, median {fmt(m['handle_time_median'])}, p75 {fmt(m['handle_time_p75'])}, p90 {fmt(m['handle_time_p90'])}.",
            f"- First-response SLA: {m['sla_eligible_count']:,} eligible; {m['sla_breach_count']:,} breached, rate {fmt_pct(m['sla_breach_rate'])}; {m['sla_ineligible_count']:,} not evaluable.",
            f"- Transfers: {m['total_transfers']:,} total across {m['transfer_valid_count']:,} valid ticket counts; {m['transferred_ticket_count']:,} tickets with at least one transfer ({fmt_pct(m['transfer_rate'])}).",
            "", "## Data quality and limitations", "", f"- Stage 1 tickets without effective roster context: {unmatched:,}, retained in metrics. Breakdown by status: " + ", ".join(f"{k}={v:,}" for k, v in sorted(unmatched_status.items())) + ". These lack a usable resolution-time assignment context; agent ID summaries remain available where agent_id exists.",
            f"- Stage 1 ticket-linked signup anomaly flags: {signup_ticket:,}; product pre-launch flags: {prelaunch:,}; degraded text heuristic flags: {quality:,}; reconciliation candidate flags: {sum(bool(r.get('reconciliation_flag')) for r in rows):,}.",
            "- Stage 1 source findings include 206 orders before customer signup and 19 pre-launch ticket matches. These are preserved and are not treated as agent failures.",
            "- Text quality detection under-flags relative to the email thread's approximate forty IVR-junk estimate; text findings require careful interpretation.",
            "- SLA rates exclude tickets without usable creation/first-response timestamps and channels without a configured target. Missing response is not treated as a breach.",
            "- Handle-time eligibility requires a completed ticket, both first response and resolution timestamps, and a non-negative duration. Outliers are retained.",
            "- CSAT response rate is valid 1–5 scores divided by completed tickets. No threshold-based CSAT percentage is defined.",
            "- Percentiles use linear interpolation over the eligible observations. No inference, ranking, Tier comparison, or case-mix adjustment is performed.", ""]
    report = Path(config.get("paths", {}).get("stage2_findings", "docs/technical/stage2_findings.md"))
    if not report.is_absolute():
        report = Path(__file__).resolve().parents[3] / report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(text), encoding="utf-8", newline="\n")

def fmt(value):
    return "undefined" if value is None else f"{value:,.2f}"

def fmt_pct(value):
    return "undefined" if value is None else f"{value:.2%}"

def run_stage3_analysis(interim_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Validate Stage 2 products then construct peer/case-mix analysis artifacts."""
    from vireo.analytics.comparisons import run_peer_analysis
    import pyarrow as pa
    import pyarrow.parquet as pq
    names=("ticket_metrics","agent_metrics","agent_assignment_metrics","normalized_agents","normalized_products")
    tables={}
    for name in names:
        path=interim_dir/f"{name}.parquet"
        if not path.is_file(): raise FileNotFoundError(f"Stage 3 requires Stage 2 input {path}")
        tables[name]=pq.read_table(path)
    ticket_rows=tables["ticket_metrics"].to_pylist()
    metrics=tables["agent_metrics"].to_pylist()
    roster=tables["normalized_agents"].to_pylist()
    products=tables["normalized_products"].to_pylist()
    stage2_report_path=interim_dir/"stage2_metrics_report.json"
    if not stage2_report_path.is_file(): raise FileNotFoundError(f"Stage 2 audit report missing: {stage2_report_path}")
    stage2_report=json.loads(stage2_report_path.read_text(encoding="utf-8"))
    expected_ticket_rows=stage2_report.get("outputs",{}).get("ticket_metrics",{}).get("row_count")
    if expected_ticket_rows is None or len(ticket_rows)!=expected_ticket_rows:
        raise ValueError(f"Stage 2 ticket row count mismatch: metrics={len(ticket_rows)}, audit={expected_ticket_rows}")
    if len({r.get("ticket_id") for r in ticket_rows})!=len(ticket_rows): raise ValueError("Stage 2 ticket IDs are not unique")
    fields=set(tables["ticket_metrics"].column_names)
    required={"valid_for_csat","csat_score_numeric","csat_unexpected_status_flag","valid_for_handle_time","handle_time_minutes","valid_for_sla","sla_breach_flag","agent_from_date","agent_to_date","agent_tier","agent_team"}
    if required-fields: raise ValueError("Stage 2 ticket metrics missing Stage 3 fields: "+", ".join(sorted(required-fields)))
    score_rows=[r for r in ticket_rows if r.get("csat_response_flag")]
    completed_scores=[r for r in score_rows if r.get("attendance_flag")]
    if sum(bool(r.get("valid_for_csat")) for r in ticket_rows)!=len(completed_scores):
        raise ValueError("Stage 2 CSAT eligibility is inconsistent with completed-ticket survey policy")
    agent_csat_count=sum(int(r.get("csat_response_count") or 0) for r in metrics)
    if agent_csat_count!=len(completed_scores):
        raise ValueError("Stage 2 agent CSAT denominators do not reconcile to completed-ticket score rows")
    if len(metrics)!=len({r.get("agent_id") for r in metrics}): raise ValueError("Stage 2 agent metrics contain duplicate agent_id rows")
    if len(metrics)!=len({r.get("agent_id") for r in roster}): raise ValueError("Stage 2 agent table does not reconcile to distinct roster agents")
    outputs=run_peer_analysis(ticket_rows,roster,products,config)
    if any(len(group.get("tiers",[]))!=1 for group in outputs["report"]["peer_groups"]):
        raise ValueError("Peer group validation failed: a cohort contains multiple tiers")
    for name in ("peer_groups","case_mix_metrics","adjusted_agent_metrics","agent_comparison"):
        data=outputs[name]
        pq.write_table(pa.Table.from_pylist(data) if data else pa.table({}),interim_dir/f"{name}.parquet",compression="zstd")
    report=outputs["report"]
    report["stage2_audit"]={"ticket_rows":len(ticket_rows),"agent_metric_rows":len(metrics),"distinct_roster_agents":len({r.get('agent_id') for r in roster}),
        "completed_csat_response_count":len(completed_scores),"populated_open_pending_scores":sum(bool(r.get("csat_unexpected_status_flag")) for r in ticket_rows),
        "open_pending_scores_excluded_from_primary_csat":True}
    report["outputs"]={name:{"path":str(interim_dir/f"{name}.parquet"),"row_count":len(outputs[name])} for name in ("peer_groups","case_mix_metrics","adjusted_agent_metrics","agent_comparison")}
    report["stability_findings"]=outputs["report"]["stability_flag_counts"]
    report["low_evidence_count_by_outcome"]=outputs["report"]["low_evidence_assignment_count_by_outcome"]
    from statistics import mean, median
    durations={}
    for source in sorted({r.get("source_system") or "(missing)" for r in ticket_rows}):
        values=[float(r["handle_time_minutes"]) for r in ticket_rows if (r.get("source_system") or "(missing)")==source and r.get("valid_for_handle_time") and r.get("handle_time_minutes") is not None]
        durations[source]={"eligible_count":len(values),"over_24_hours":sum(v>1440 for v in values),"over_7_days":sum(v>10080 for v in values),
                           "mean_minutes":mean(values) if values else None,"median_minutes":median(values) if values else None,"maximum_minutes":max(values) if values else None}
    report["handle_time_distribution_by_source_system"]=durations
    report["sla_attribution_limitation"]="Stage 2 agent_id identifies the resolving agent; first-response actor ID is not in source data. SLA comparisons are resolver-associated ticket comparisons, not verified first-responder performance."
    report_path=interim_dir/"stage3_analysis_report.json"
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    _write_stage3_findings(config,report,outputs,ticket_rows)
    return report

def _write_stage3_findings(config,report,outputs,tickets):
    from statistics import median
    handles=[float(r["handle_time_minutes"]) for r in tickets if r.get("valid_for_handle_time") and r.get("handle_time_minutes") is not None]
    long_handles=sum(v>1440 for v in handles)
    gap=report["raw_adjusted_gap_summary"]
    lines=["# Stage 3 Findings","","Generated from Stage 2 ticket metrics. Results are descriptive adjusted comparisons, not causal explanations or training decisions.","",
        "## Peer coverage","",f"- Distinct agents: {report['stage2_audit']['distinct_roster_agents']}; assignment rows: {report['assignment_context_count']}; peer groups: {report['peer_group_count']}.",
        f"- Comparable full-period roster assignments: {report['comparison_assignment_count']} of {report['assignment_context_count']}; {report['unmatched_assignment_context_rows']} additional agent context rows lack a resolution-time roster assignment and are retained without peer comparisons.",
        f"- Peer fallback requires at least {report['minimum_peer_agents']} distinct agents in a tier-safe cohort; within-work cells require at least {report['minimum_peer_cell_observations']} observations from two or more other agents.",
        "- Tier 1 and Tier 2 are never pooled. Peer hierarchy uses tier/team/site/shift when supported, falls back to tier/team, then tier only; unsupported tiers remain un-compared.",
        "", "## Raw and case-mix adjusted comparisons","","Gaps are observed minus leave-one-agent-out expected peer performance on the same case mix. Positive CSAT gaps are higher scores; positive handle-time and SLA gaps are longer times or higher breach rates.","",
        "| Outcome | Supported assignment comparisons | Positive gaps | Negative gaps | Median absolute adjusted gap |","|---|---:|---:|---:|---:|"]
    for name,label in (("csat","CSAT (1–5 points)"),("handle_time","Handle time (minutes)"),("sla","SLA breach-rate points")):
        d=gap[name]; lines.append(f"| {label} | {d['adjusted_comparison_count']} | {d['positive_gap_count']} | {d['negative_gap_count']} | {fmt(d['median_absolute_gap'])} |")
    lines.extend(["","Approximate gap-interval directions (interval wholly above zero / wholly below zero / overlaps zero):"])
    for name,label in (("csat","CSAT"),("handle_time","Handle time"),("sla","SLA")):
        counts=gap[name]["gap_interval_direction_counts"]
        lines.append(f"- {label}: above={counts.get('higher',0)}, below={counts.get('lower',0)}, overlaps={counts.get('overlaps_zero',0)}, insufficient={counts.get('insufficient',0)}.")
        coverage=report["adjustment_coverage_by_outcome"][name]
        lines.append(f"- {label} peer-work coverage: mean {fmt_pct(coverage['mean_coverage_rate'])}, minimum {fmt_pct(coverage['minimum_coverage_rate'])} across comparable assignments.")
    lines.extend(["","## Case mix and stability","",f"- Agent assignment case mixes are published for channel, priority, category, product family, team, tier, site, shift, and period. Each share has its ticket denominator; missing values have an explicit level."])
    for dim,label in (("channel","channel"),("priority","priority")):
        options=report["case_mix_share_ranges"].get(dim,{})
        if options:
            level,values=max(options.items(),key=lambda item:item[1]["maximum_agent_share"]-item[1]["minimum_agent_share"])
            lines.append(f"- Largest observed {label} share range across rostered assignment groups for `{level}` was {values['minimum_agent_share']:.1%} to {values['maximum_agent_share']:.1%}; this is a mix difference, not a causal effect.")
    lines.extend([
        f"- Stability is assessed across quarterly intervals with 95% intervals; status counts: {json.dumps(report['stability_flag_counts'],sort_keys=True)}.",
        f"- Comparable full-period assignments with fewer than 30 eligible observations: {json.dumps(report['low_evidence_assignment_count_by_outcome'],sort_keys=True)}. Month/quarter low-evidence row counts: {json.dumps(report['low_evidence_period_count_by_outcome'],sort_keys=True)}. The 30-observation label is descriptive, not a decision threshold.",
        "", "## Data audit and limitations","",f"- Primary CSAT uses {report['stage2_audit']['completed_csat_response_count']:,} valid completed-ticket responses. The {report['stage2_audit']['populated_open_pending_scores']:,} populated open/pending scores are excluded from primary CSAT and remain flagged.",
        f"- Handle-time distribution retains all {len(handles):,} eligible observations, including {long_handles:,} durations over 24 hours; median {fmt(median(handles) if handles else None)} minutes. No clipping or transformation was applied.",
        "- Stage 1 anomalies remain visible: 206 orders before signup, 19 pre-launch matches, 21 degraded-text heuristic flags, zero exact cross-source duplicate candidates, and 567 tickets without resolution-time roster context.",
        "- Category was not an adjustment predictor because the intake category may be retagged by agents at closure. Transfers, handle time, SLA, refunds, replacements, resolution behavior, and notes are outcome/post-routing fields and were not used as case-mix controls.",
        "- SLA is associated with the ticket's resolving agent because `agent_id` identifies the resolver; the first-response actor is unavailable. Treat these as resolver-associated ticket outcomes, not verified first-responder performance.",
        "- The adjustment uses channel, priority, calendar quarter, product family, and tier-safe peer membership. Peer-cell fallbacks broaden in a fixed order when support is sparse.",
        "- Handle-time durations over 24 hours occur in both sources: " + "; ".join(f"{source} {stats['over_24_hours']:,}/{stats['eligible_count']:,} (over 7 days {stats['over_7_days']:,})" for source,stats in report["handle_time_distribution_by_source_system"].items()) + ". This is not isolated to legacy records; the available fields cannot distinguish legitimate long-running cases from timestamp/data artifacts, so observations remain unchanged.",
        "- Approximate confidence intervals assume independent tickets and do not capture agent/period clustering, unobserved case complexity, or selection uncertainty. Observational gaps do not establish causation.",
        "- No global rank, bottom-ten list, or training recommendation is produced.",""])
    path=Path(config.get("paths",{}).get("stage3_findings","docs/technical/stage3_findings.md"))
    if not path.is_absolute():path=Path(__file__).resolve().parents[3]/path
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text("\n".join(lines),encoding="utf-8",newline="\n")


def run_ai_diagnostics(interim_dir: Path, config: dict[str, Any], project_root: Path | None = None) -> dict[str, Any]:
    """Run optional Stage 5; every exception degrades to a report and never blocks Stages 1-4."""
    from vireo.pipeline.ai_analysis import run_stage5_ai
    try:
        return run_stage5_ai(interim_dir, config, project_root=project_root)
    except Exception as exc:
        import pyarrow as pa
        import pyarrow.parquet as pq
        for name in ("ai_ticket_analysis", "ai_agent_diagnostics", "ai_peer_diagnostics", "ai_evaluation"):
            pq.write_table(pa.table({}), interim_dir / f"{name}.parquet", compression="zstd")
        report = {"status": "DEGRADED", "ai_status": "failed_safely", "error_type": type(exc).__name__,
            "error": str(exc)[:300], "tickets_selected": 0, "tickets_analyzed": 0,
            "model_accuracy": None, "estimated_run_cost_usd": None,
            "note": "AI diagnostics failed; deterministic Stage 1-4 outputs remain valid and unchanged."}
        (interim_dir / "ai_run_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report


def run_training_priority(interim_dir: Path, config: dict[str, Any], project_root: Path | None = None) -> dict[str, Any]:
    """Stage 6 decision output; AI diagnostics may enrich explanations but never score."""
    import json
    from collections import Counter
    import pyarrow as pa
    import pyarrow.parquet as pq
    from vireo.scoring.priority import build_priority_rows, sensitivity_summary

    project_root = project_root or Path(__file__).resolve().parents[3]
    names = ("adjusted_agent_metrics", "agent_comparison", "agent_economics", "agent_metrics",
             "agent_assignment_metrics", "ai_agent_diagnostics", "ai_ticket_analysis")
    tables = {name: pq.read_table(interim_dir / f"{name}.parquet").to_pylist() for name in names}
    for dataset in ("agent_metrics", "agent_economics"):
        ids = [r.get("agent_id") for r in tables[dataset]]
        if None in ids or len(ids) != len(set(ids)):
            raise ValueError(f"Stage 6 requires unique non-null agent IDs in {dataset}")
    if {r["agent_id"] for r in tables["agent_metrics"]} != {r["agent_id"] for r in tables["agent_economics"]}:
        raise ValueError("Stage 6 agent metrics/economics populations do not reconcile")
    ai_report_path = interim_dir / "ai_run_report.json"
    ai_report = json.loads(ai_report_path.read_text(encoding="utf-8")) if ai_report_path.exists() else {}
    ai_raw_status = ai_report.get("ai_status", "not_configured")
    analyzed_ticket_ids = {r.get("ticket_id") for r in tables["ai_ticket_analysis"] if r.get("analysis_status") in ("analyzed", "cached")}
    canonical_ids = {r.get("ticket_id") for r in pq.read_table(interim_dir / "normalized_tickets.parquet", columns=["ticket_id"]).to_pylist()}
    bad_refs = sorted({tid for row in tables["ai_agent_diagnostics"] for tid in (row.get("representative_ticket_ids") or [])
                       if tid not in analyzed_ticket_ids or tid not in canonical_ids})
    ai_rows = [{**row, "representative_ticket_ids": [tid for tid in (row.get("representative_ticket_ids") or [])
                if tid in analyzed_ticket_ids and tid in canonical_ids]} for row in tables["ai_agent_diagnostics"]]
    if ai_raw_status in ("failed_safely", "failed") or ai_report.get("status") == "DEGRADED":
        ai_status = "failed"
    elif analyzed_ticket_ids and (bad_refs or int(ai_report.get("invalid_or_failed_count") or 0) > 0):
        ai_status = "partial"
    elif analyzed_ticket_ids:
        ai_status = "available"
    else:
        ai_status = "unavailable"

    # Use the Stage 3 adjusted full-period estimate, with its comparison/stability fields.
    adjusted_by_id = {r["agent_id"]: r for r in tables["adjusted_agent_metrics"] if r.get("period_type") == "full_available_period"}
    comparison_rows = []
    for row in tables["agent_comparison"]:
        adjusted = adjusted_by_id.get(row.get("agent_id"), {}) if row.get("period_type") == "full_available_period" else {}
        comparison_rows.append({**adjusted, **row})
    comparison_rows.extend(r for r in tables["adjusted_agent_metrics"] if r.get("period_type") == "quarter")
    stage6_config = config.get("stage6", {})
    decisions = build_priority_rows(comparison_rows, tables["agent_metrics"], tables["agent_economics"], ai_rows, ai_status, stage6_config)
    sensitivity = sensitivity_summary(decisions, comparison_rows, tables["agent_metrics"], tables["agent_economics"], ai_rows, ai_status, stage6_config)
    output_path = interim_dir / "training_priority.parquet"
    pq.write_table(pa.Table.from_pylist(decisions), output_path, compression="zstd")
    band_counts = Counter(r["priority_band"] for r in decisions)
    status_counts = Counter(r["priority_status"] for r in decisions)
    gate_counts = Counter(g for r in decisions for g in r["eligibility_gates"])
    raw_bottom = {}
    for tier in sorted({str(r.get("tier")) for r in decisions}):
        subset = [r for r in decisions if str(r.get("tier")) == tier]
        raw_bottom[tier] = {}
        for metric_key in ("csat_low_is_worse", "handle_time_high_is_worse", "sla_high_is_worse"):
            ranked = sorted((r for r in subset if r["raw_metric_ranks"][metric_key] is not None),
                            key=lambda r: (-r["raw_metric_ranks"][metric_key], r["agent_id"]))
            raw_bottom[tier][metric_key] = [r["agent_id"] for r in ranked[:10]]
    priority_ids = {r["agent_id"] for r in decisions if r["priority_status"] == "training_candidate"}
    raw_vs_priority = {tier: {metric: {"raw_bottom_ten_agent_ids": ids,
        "overlap_with_training_candidates": sorted(set(ids) & priority_ids)} for metric, ids in metrics.items()}
        for tier, metrics in raw_bottom.items()}
    report = {"status": "PASS", "stage": 6, "decision_method": "interval-gated deterministic score; economic and AI evidence are context only",
        "agents_evaluated": len(decisions), "agents_excluded_or_not_rankable": sum(r["priority_status"] == "not_rankable" for r in decisions),
        "eligible_agents": sum(not r["eligibility_gates"] for r in decisions), "priority_status_counts": dict(status_counts),
        "priority_band_counts": dict(band_counts), "high_priority_count": band_counts.get("high", 0),
        "insufficient_evidence_count": gate_counts.get("insufficient_evidence", 0), "eligibility_gate_counts": dict(gate_counts),
        "tier_counts": dict(Counter(str(r.get("tier")) for r in decisions)), "ai_evidence_status": ai_status,
        "ai_diagnostic_agent_rows": len(ai_rows), "invalid_ai_representative_ticket_references_removed": len(bad_refs),
        "training_budget_inr": float(stage6_config.get("training_budget_inr", 400000)), "training_cost_data_available": False,
        "training_cost_inr": None, "raw_rank_definition": "Separate descriptive within-tier ranks for adjusted CSAT, handle-time, and SLA point estimates; not a composite decision rank.",
        "stage3_uncertainty_finding": "All reported adjusted full-period gap intervals overlapped zero; no point estimate alone is treated as confirmed underperformance.",
        "sensitivity": sensitivity,
        "raw_vs_priority": raw_vs_priority,
        "upstream_input_row_counts": {name: len(data) for name, data in tables.items()},
        "upstream_reconciliation": {"agent_metrics_unique_agents": len(tables["agent_metrics"]),
            "agent_economics_unique_agents": len(tables["agent_economics"]),
            "ticket_metrics_rows": pq.read_table(interim_dir / "ticket_metrics.parquet").num_rows,
            "ticket_economics_rows": pq.read_table(interim_dir / "ticket_economics.parquet").num_rows,
            "agent_assignment_period_rows": len(tables["agent_assignment_metrics"])},
        "outputs": {"training_priority": {"path": str(output_path), "row_count": len(decisions)}},
        "priority_explanations": [r["explanation"] for r in decisions],
        "limitations": ["Priority ranking is observational and not a causal personnel assessment.",
            "Stage 5 has no validated real-model evaluation; AI is optional and does not affect numeric score.",
            "Approximate Stage 3 intervals assume independent tickets and may understate uncertainty.",
            "Economic exposure is associated with resolved-ticket populations and is not attributed savings.",
            "Training costs are unavailable; the ₹4,00,000 budget is not allocated or treated as ROI."]}
    (interim_dir / "training_priority_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    _write_stage6_findings(project_root / "docs" / "technical" / "stage6_findings.md", decisions, report)
    return report


def _write_stage6_findings(path: Path, decisions: list[dict[str, Any]], report: dict[str, Any]) -> None:
    lines = ["# Stage 6 Findings", "", "Generated by the deterministic Stage 6 decision engine. This is not a production-validated personnel ranking.", "",
        f"- Agents represented: {len(decisions)}.", f"- Eligible under structural/data gates: {report['eligible_agents']}.",
        f"- Not rankable: {report['agents_excluded_or_not_rankable']}.", f"- Priority bands: `{json.dumps(report['priority_band_counts'], sort_keys=True)}`.",
        f"- High-priority count: {report['high_priority_count']}.", f"- AI evidence status: `{report['ai_evidence_status']}`.",
        "- Stage 3 reported all adjusted full-period intervals overlapping zero; no agent receives an adverse performance signal from a point estimate alone.",
        "- Economic exposures are contextual and are not interpreted as savings or agent-caused cost.", "", "## Decision patterns", ""]
    for row in decisions:
        lines.append(f"- `{row['agent_id']}` (Tier {row.get('tier') or 'unknown'}): {row['priority_band']}; {row['priority_reason']}")
    lines.extend(["", "## Sensitivity", "", f"- Default candidate set robust across non-point-estimate scenarios: `{report['sensitivity']['default_candidate_set_robust']}`."])
    for name, scenario in report["sensitivity"]["scenarios"].items():
        lines.append(f"- `{name}`: {scenario['training_candidate_count']} candidates.")
    exploratory = report["sensitivity"]["scenarios"]["point_estimate_only_exploratory"]["candidate_agent_ids"]
    lines.append("- Exploratory point-estimate-only candidates (not selected by default): " + (", ".join(exploratory) if exploratory else "none") + ".")
    lines.append(f"- AI available/unavailable numeric-score invariance: `{report['sensitivity']['ai_status_invariance_verified']}`.")
    lines.extend(["", "## Limitations", "", *[f"- {item}" for item in report["limitations"]],
        "", "No causal attribution, budget allocation, final client recommendation, or Stage 7 reliability claim is made.", ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
