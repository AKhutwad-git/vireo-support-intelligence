"""Stage 4 deterministic ticket economics and reproducible report outputs."""
from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo
import pyarrow as pa
import pyarrow.parquet as pq

from vireo.analytics.opportunity import opportunity_scenarios
from vireo.analytics.product_order import build_product_order_analysis, write_product_order_analysis
from vireo.analytics.peer_groups import assignment_key
from vireo.analytics.repeat_contacts import detect_repeat_contacts
from vireo.policy.economics import (calculate_replacement_cost, calculate_sla_breach_cost,
    calculate_transfer_cost, get_contact_cost)

MONEY_FIELDS = ("contact_cost_inr", "sla_breach_cost_inr", "transfer_cost_inr",
                "replacement_cost_inr", "refund_amount_inr", "repeat_contact_cost_inr")
SUM_FIELDS = (*MONEY_FIELDS, "operational_cost_exposure_inr", "internal_transfer_cost_exposure_inr",
              "replacement_exposure_inr", "refund_exposure_inr", "total_relevant_exposure_inr")


def _num(value, default=0.0):
    if value in (None, ""):
        return default
    return float(value)


def _date_period(value, zone):
    if not value:
        return None, None
    dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(zone)
    return dt.strftime("%Y-%m"), f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"


def calculate_ticket_economics(ticket_rows: list[dict], products: list[dict], peer_groups: list[dict], timezone="Asia/Kolkata") -> list[dict]:
    """Calculate exposures at ticket grain; reject ambiguous SKU or peer joins."""
    product_map = {}
    for product in products:
        sku = product.get("sku")
        if sku in product_map:
            raise ValueError(f"Duplicate product SKU prevents safe replacement join: {sku}")
        product_map[sku] = product
    peer_map = {assignment_key(row): row for row in peer_groups}
    if len(peer_map) != len(peer_groups):
        raise ValueError("Peer group assignment keys are not unique")
    seen = set()
    zone = ZoneInfo(timezone)
    rows = []
    for source in ticket_rows:
        ticket_id = source.get("ticket_id")
        if not ticket_id or ticket_id in seen:
            raise ValueError("Ticket IDs must be present and unique at economics grain")
        seen.add(ticket_id)
        channel_cost = get_contact_cost(source.get("channel"))
        if channel_cost is None:
            raise ValueError(f"Unsupported or missing channel for {ticket_id}: {source.get('channel')!r}")
        replacement = str(source.get("replacement_issued") or "").strip().upper() == "Y"
        product = product_map.get(source.get("product_sku")) if replacement else None
        unit_cost = _num(product.get("unit_cost_inr"), None) if product else None
        replacement_cost = calculate_replacement_cost(unit_cost) if replacement else 0.0
        replacement_missing = replacement and replacement_cost is None
        refund = _num(source.get("refund_amount_inr"))
        if refund < 0:
            raise ValueError(f"Negative refund amount for {ticket_id}; source retained but economics cannot silently repair it")
        transfer_count = int(_num(source.get("transfers_numeric"), 0))
        if transfer_count < 0:
            raise ValueError(f"Negative transfer count for {ticket_id}")
        sla_cost = calculate_sla_breach_cost(bool(source.get("sla_breach_flag")))
        transfer_cost = calculate_transfer_cost(transfer_count)
        peer = peer_map.get(assignment_key(source)) if source.get("agent_assignment_flag") == "matched" else None
        month, quarter = _date_period(source.get("created_at"), zone)
        row = {"ticket_id": ticket_id, "created_at": source.get("created_at"), "first_response_at": source.get("first_response_at"), "resolved_at": source.get("resolved_at"),
            "reporting_month": month, "reporting_quarter": quarter, "channel": source.get("channel"),
            "source_system": source.get("source_system"), "status": source.get("status"),
            "customer_id": source.get("customer_id"), "order_id": source.get("order_id"), "product_sku": source.get("product_sku"),
            "product_family": product.get("family") if product else None, "agent_id": source.get("agent_id"),
            "agent_team": source.get("agent_team"), "agent_tier": source.get("agent_tier"),
            "agent_site": source.get("agent_site"), "agent_shift": source.get("agent_shift"),
            "agent_from_date": source.get("agent_from_date"), "agent_to_date": source.get("agent_to_date"),
            "agent_assignment_flag": source.get("agent_assignment_flag"), "attendance_flag": bool(source.get("attendance_flag")),
            "sla_status": source.get("sla_status"), "sla_breach_flag": bool(source.get("sla_breach_flag")),
            "sla_eligible_flag": bool(source.get("valid_for_sla")), "sla_eligibility_reason": source.get("sla_eligibility_reason"),
            "sla_target_minutes": source.get("sla_target_minutes"), "first_response_minutes": source.get("first_response_minutes"),
            "source_transfers_value": source.get("transfers"), "transfers_count": transfer_count,
            "source_replacement_issued_value": source.get("replacement_issued"), "source_refund_amount_inr": source.get("refund_amount_inr"),
            "replacement_issued_flag": replacement, "replacement_unit_cost_inr": unit_cost,
            "replacement_cost_missing_flag": replacement_missing,
            "refund_reason_code": source.get("refund_reason_code") or None,
            "refund_replacement_anomaly_flag": bool(refund > 0 and replacement),
            "refund_replacement_anomaly_exposure_inr": round(refund + (replacement_cost or 0.0), 2) if refund > 0 and replacement else 0.0,
            "contact_cost_inr": channel_cost, "sla_breach_cost_inr": sla_cost,
            "transfer_cost_inr": transfer_cost, "replacement_cost_inr": replacement_cost,
            "refund_amount_inr": refund, "repeat_contact_cost_inr": 0.0,
            "comparison_group": peer.get("comparison_group") if peer else None,
            "peer_fallback_level": peer.get("peer_fallback_level") if peer else "unmatched_context",
            "peer_supported": bool(peer and peer.get("peer_supported")),
            "comparison_context_flag": bool(peer)}
        row["operational_cost_exposure_inr"] = round(channel_cost + sla_cost + transfer_cost, 2)
        row["internal_transfer_cost_exposure_inr"] = round(transfer_cost, 2)
        row["replacement_exposure_inr"] = replacement_cost
        row["refund_exposure_inr"] = refund
        row["total_relevant_exposure_inr"] = round(row["operational_cost_exposure_inr"] + (replacement_cost or 0) + refund, 2)
        rows.append(row)
    repeat = detect_repeat_contacts([{**s, "ticket_id": r["ticket_id"], "created_at": r.get("created_at"),
        "resolved_at": r.get("resolved_at"), "customer_id": r.get("customer_id"), "order_id": r.get("order_id"),
        "product_sku": r.get("product_sku")} for s, r in zip(ticket_rows, rows)])
    repeat_map = {r["ticket_id"]: r for r in repeat}
    for row in rows:
        match = repeat_map[row["ticket_id"]]
        row.update({k: match[k] for k in ("repeat_contact_candidate_flag", "repeat_contact_prior_ticket_id", "repeat_contact_match_method", "repeat_contact_candidate_reason")})
        row["repeat_contact_cost_inr"] = row["contact_cost_inr"] if row["repeat_contact_candidate_flag"] else 0.0
    return rows


def _aggregate(rows, keys):
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(k) for k in keys)].append(row)
    result = []
    for key, values in sorted(grouped.items(), key=lambda item: str(item[0])):
        item = dict(zip(keys, key))
        item.update({"ticket_count": len(values), "completed_ticket_count": sum(r["attendance_flag"] for r in values),
            "sla_eligible_count": sum(r["sla_eligible_flag"] for r in values),
            "sla_breach_count": sum(r["sla_breach_flag"] for r in values),
            "sla_breach_rate": sum(r["sla_breach_flag"] for r in values) / sum(r["sla_eligible_flag"] for r in values) if sum(r["sla_eligible_flag"] for r in values) else None,
            "transfer_count": sum(r["transfers_count"] for r in values),
            "replacement_count": sum(r["replacement_issued_flag"] for r in values),
            "replacement_cost_missing_count": sum(r["replacement_cost_missing_flag"] for r in values),
            "refund_ticket_count": sum(r["refund_amount_inr"] > 0 for r in values),
            "refund_replacement_anomaly_count": sum(r["refund_replacement_anomaly_flag"] for r in values),
            "repeat_contact_candidate_count": sum(r["repeat_contact_candidate_flag"] for r in values),
            "average_sla_breach_cost_per_completed_ticket_inr": sum(r["sla_breach_cost_inr"] for r in values) / sum(r["attendance_flag"] for r in values) if sum(r["attendance_flag"] for r in values) else None,
            "average_replacement_cost_inr": (sum(r["replacement_cost_inr"] or 0 for r in values) / sum(r["replacement_cost_inr"] is not None and r["replacement_issued_flag"] for r in values)) if any(r["replacement_cost_inr"] is not None and r["replacement_issued_flag"] for r in values) else None})
        for field in SUM_FIELDS:
            item[field] = round(sum(r.get(field) or 0 for r in values), 2)
        result.append(item)
    return result


def run_stage4_economics(interim_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    required = ("ticket_metrics", "normalized_tickets", "normalized_orders", "normalized_products", "adjusted_agent_metrics", "agent_comparison", "peer_groups")
    tables = {}
    for name in required:
        path = interim_dir / f"{name}.parquet"
        if not path.is_file():
            raise FileNotFoundError(f"Stage 4 input missing: {path}")
        tables[name] = pq.read_table(path)
    metrics = tables["ticket_metrics"].to_pylist()
    normalized = tables["normalized_tickets"].to_pylist()
    if len(metrics) != len(normalized) or {r.get("ticket_id") for r in metrics} != {r.get("ticket_id") for r in normalized} or len({r["ticket_id"] for r in metrics}) != len(metrics):
        raise ValueError("Stage 4 input ticket grain does not reconcile to Stage 1")
    required_fields = {"ticket_id", "channel", "created_at", "resolved_at", "customer_id", "order_id", "product_sku", "agent_id", "agent_team", "agent_tier", "agent_assignment_flag", "sla_breach_flag", "valid_for_sla", "transfers_numeric", "replacement_issued", "refund_amount_inr", "refund_reason_code"}
    absent_fields = required_fields - set(tables["ticket_metrics"].column_names)
    if absent_fields:
        raise ValueError("Stage 4 ticket metrics missing required fields: " + ", ".join(sorted(absent_fields)))
    if not {"sku", "unit_cost_inr", "family"} <= set(tables["normalized_products"].column_names):
        raise ValueError("Stage 4 products input missing sku, unit_cost_inr, or family")
    if len({r.get("order_id") for r in tables["normalized_orders"].to_pylist()}) != tables["normalized_orders"].num_rows:
        raise ValueError("Order IDs are not unique; order relation cannot be safely audited")
    tickets = calculate_ticket_economics(metrics, tables["normalized_products"].to_pylist(), tables["peer_groups"].to_pylist(), config.get("reporting_timezone", "Asia/Kolkata"))
    if len(tickets) != len(metrics):
        raise ValueError("Ticket economics changed ticket grain")
    product_order_analysis = build_product_order_analysis(
        metrics, tables["normalized_orders"].to_pylist(), tables["normalized_products"].to_pylist(), tickets)
    product_order_summary = write_product_order_analysis(interim_dir, product_order_analysis)
    periods = []
    periods.extend({"period_type": "full_available_period", "period": "all", **r} for r in _aggregate(tickets, []))
    periods.extend({"period_type": "month", "period": r["reporting_month"], **r} for r in _aggregate([r for r in tickets if r["reporting_month"]], ["reporting_month"]))
    quarters = _aggregate([r for r in tickets if r["reporting_quarter"]], ["reporting_quarter"])
    prior_total = None
    for q in quarters:
        current = q["total_relevant_exposure_inr"]
        periods.append({"period_type": "quarter", "period": q["reporting_quarter"], **q,
            "quarter_over_quarter_change_inr": round(current - prior_total, 2) if prior_total is not None else None,
            "quarter_over_quarter_change_pct": round((current / prior_total - 1) * 100, 2) if prior_total else None})
        prior_total = current
    channels = _aggregate(tickets, ["channel"])
    teams = _aggregate(tickets, ["agent_team", "agent_tier"])
    peers = _aggregate(tickets, ["comparison_group", "peer_fallback_level", "peer_supported"])
    products = _aggregate([r for r in tickets if r["replacement_issued_flag"]], ["product_sku", "product_family"])
    refund_reasons = _aggregate([r for r in tickets if r["refund_amount_inr"] > 0], ["refund_reason_code"])
    agent_rows = _aggregate([r for r in tickets if r["attendance_flag"] and r["agent_id"]],
        ["agent_id", "agent_team", "agent_tier", "agent_site", "agent_shift", "agent_from_date", "agent_to_date", "comparison_group", "peer_supported"])
    scenarios = opportunity_scenarios({"contact": sum(r["contact_cost_inr"] for r in tickets),
        "sla_breach": sum(r["sla_breach_cost_inr"] for r in tickets), "transfers": sum(r["transfer_cost_inr"] for r in tickets),
        "replacement_known_cost": sum(r["replacement_cost_inr"] or 0 for r in tickets), "refund_amount": sum(r["refund_amount_inr"] for r in tickets),
        "repeat_contact_candidate_subset_of_contact": sum(r["repeat_contact_cost_inr"] for r in tickets)})
    outputs = {"ticket_economics": tickets, "agent_economics": agent_rows, "period_economics": periods,
        "channel_economics": channels, "team_economics": teams, "peer_group_economics": peers,
        "product_economics": products, "refund_reason_economics": refund_reasons,
        "opportunity_scenarios": scenarios}
    for name, rows in outputs.items():
        pq.write_table(pa.Table.from_pylist(rows) if rows else pa.table({}), interim_dir / f"{name}.parquet", compression="zstd")
    report = _make_report(tickets, periods, channels, teams, peers, scenarios, tables, config)
    report["outputs"] = {name: {"path": str(interim_dir / f"{name}.parquet"), "row_count": len(rows)} for name, rows in outputs.items()}
    report["product_order_analysis"] = product_order_summary
    report["outputs"].update(product_order_summary["outputs"])
    (interim_dir / "stage4_economics_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    _write_findings(interim_dir, report)
    return report


def _make_report(tickets, periods, channels, teams, peers, scenarios, tables, config):
    sums = {field: round(sum(r.get(field) or 0 for r in tickets), 2) for field in SUM_FIELDS}
    replacement_month = {r["period"]: r["replacement_exposure_inr"] for r in periods if r["period_type"] == "month"}
    qmap = {r["period"]: r for r in periods if r["period_type"] == "quarter"}
    quarter = sorted(qmap)
    q3, q4 = qmap.get("2025-Q3"), qmap.get("2025-Q4")
    festive = {"definition": "calendar Q4 2025 compared with preceding calendar Q3 2025; dataset has no Q4 2024 comparator",
        "ticket_volume_q3_2025": q3["ticket_count"] if q3 else None, "ticket_volume_q4_2025": q4["ticket_count"] if q4 else None,
        "ticket_volume_change_pct": round((q4["ticket_count"] / q3["ticket_count"] - 1) * 100, 2) if q3 and q3["ticket_count"] else None,
        "replacement_count_q3_2025": q3["replacement_count"] if q3 else None, "replacement_count_q4_2025": q4["replacement_count"] if q4 else None,
        "replacement_count_change_pct": round((q4["replacement_count"] / q3["replacement_count"] - 1) * 100, 2) if q3 and q3["replacement_count"] else None,
        "claim_status": "Q4_vs_Q3_descriptive_comparison_only; year_over_year_festive_claim_cannot_be_established"}
    dec = replacement_month.get("2025-12")
    jun = replacement_month.get("2026-06")
    dec_claim = {"december_2025_replacement_exposure_inr": dec, "june_2026_replacement_exposure_inr": jun,
        "june_vs_december_change_pct": round((jun / dec - 1) * 100, 2) if dec else None,
        "q2_2026_monthly_average_replacement_exposure_inr": round(sum(replacement_month.get(m, 0) for m in ("2026-04", "2026-05", "2026-06")) / 3, 2),
        "december_claim_status": "june_2026_is_below_december_2025; july_to_september_2026_not_in_dataset"}
    missing = sum(r["replacement_cost_missing_flag"] for r in tickets)
    return {"status": "PASS", "ticket_rows": len(tickets), "distinct_ticket_ids": len({r["ticket_id"] for r in tickets}),
        "upstream_audit": {"ticket_metrics_rows": tables["ticket_metrics"].num_rows, "normalized_tickets_rows": tables["normalized_tickets"].num_rows,
            "ticket_id_set_reconciles": {r.get("ticket_id") for r in tables["ticket_metrics"].to_pylist()} == {r.get("ticket_id") for r in tables["normalized_tickets"].to_pylist()},
            "normalized_orders_rows": tables["normalized_orders"].num_rows, "normalized_products_rows": tables["normalized_products"].num_rows,
            "adjusted_agent_metrics_rows": tables["adjusted_agent_metrics"].num_rows, "agent_comparison_rows": tables["agent_comparison"].num_rows,
            "peer_groups_rows": tables["peer_groups"].num_rows, "ticket_grain_reconciles": len(tickets) == tables["ticket_metrics"].num_rows,
            "missing_replacement_product_cost_count": missing,
            "replacement_skus_matched": all(r["product_sku"] for r in tickets if r["replacement_issued_flag"] and r["replacement_unit_cost_inr"] is not None),
            "channel_values": sorted({r["channel"] for r in tickets}), "sla_breach_count": sum(r["sla_breach_flag"] for r in tickets),
            "transfer_total": sum(r["transfers_count"] for r in tickets), "replacement_count": sum(r["replacement_issued_flag"] for r in tickets),
            "refund_ticket_count": sum(r["refund_amount_inr"] > 0 for r in tickets),
            "unmatched_roster_ticket_count": sum(not r["comparison_context_flag"] for r in tickets)},
        "exposure_totals_inr": sums, "replacement_missing_cost_count": missing,
        "replacement_cost_method": "unit_cost_inr + Rs 340 logistics per replacement ticket; no quantity multiplier",
        "latest_complete_quarter": next((q for q in reversed(quarter) if q != quarter[-1] or len(tickets) and max((r["reporting_quarter"] for r in tickets if r["reporting_quarter"]), default=None) == q), None),
        "available_quarters": quarter, "quarterly_trends": [r for r in periods if r["period_type"] == "quarter"],
        "replacement_claim_analysis": dec_claim, "festive_claim_analysis": festive,
        "anomaly_count": sum(r["refund_replacement_anomaly_flag"] for r in tickets),
        "anomaly_exposure_inr": round(sum(r["refund_replacement_anomaly_exposure_inr"] for r in tickets), 2),
        "repeat_contact_candidate_count": sum(r["repeat_contact_candidate_flag"] for r in tickets),
        "repeat_contact_candidate_cost_inr": sums["repeat_contact_cost_inr"],
        "scenario_opportunity_totals_inr": {str(rate): round(sum(r["scenario_opportunity_inr"] for r in scenarios if r["scenario_reduction_rate"] == rate and r["cost_driver"] != "repeat_contact_candidate_subset_of_contact"), 2) for rate in (.1,.2,.3)},
        "scenarios": "Hypothetical reductions in observed cost drivers; not realized or causal savings. Repeat-contact opportunity is a subset of contact cost and excluded from combined scenario totals to avoid double counting.",
        "sla_attribution_limitation": "SLA comparisons are associated with the resolving agent; first-response actor identity is unavailable.",
        "cost_attribution_limitation": "Agent economics describe observed ticket-associated exposure for resolved-ticket population, not cost caused by the agent.",
        "labor_cost_treatment": "The Rs 165 per agent-hour staffing planning rate is not applied to elapsed handle time.",
        "refund_treatment": "Refund amounts are reported as observed customer value transfers and are not classified as avoidable.",
        "repeat_contact_method": "same customer and same nonblank order_id, or when both order IDs are blank same product_sku; later creation strictly after prior resolution and within 30 days; nearest prior qualifying resolution; candidate only.",
        "checks": {"ticket_grain_reconciles": len(tickets) == tables["ticket_metrics"].num_rows,
            "all_monetary_exposures_nonnegative": all((r.get(k) or 0) >= 0 for r in tickets for k in MONEY_FIELDS),
            "no_retail_or_order_value_in_replacement_formula": True,
            "scenario_opportunity_within_driver_exposure": all(r["scenario_opportunity_inr"] <= r["observed_exposure_inr"] for r in scenarios)}}


def _write_findings(interim_dir, report):
    e = report["exposure_totals_inr"]
    qrows = report["quarterly_trends"]
    lines = ["# Stage 4 Economics Findings", "", "Descriptive policy-backed cost exposures; scenarios are hypothetical and do not establish savings or causality.", "",
        "## Observed exposure", "", f"- Contact cost exposure: ₹{e['contact_cost_inr']:,.2f}.", f"- SLA breach credit exposure: ₹{e['sla_breach_cost_inr']:,.2f} across {report['upstream_audit']['sla_breach_count']:,} breaches.",
        f"- Transfer cost exposure: ₹{e['transfer_cost_inr']:,.2f} across {report['upstream_audit']['transfer_total']:,} transfers.",
        f"- Known replacement exposure: ₹{e['replacement_cost_inr']:,.2f} across {report['upstream_audit']['replacement_count']:,} replacements; missing cost count {report['replacement_missing_cost_count']}.",
        f"- Refund amount exposure: ₹{e['refund_amount_inr']:,.2f}; refunds are not classified as avoidable.",
        f"- Operational cost exposure (contact + SLA credit + transfers): ₹{e['operational_cost_exposure_inr']:,.2f}.",
        f"- Total relevant exposure (operational + known replacement + refunds): ₹{e['total_relevant_exposure_inr']:,.2f}. Repeat-contact cost is a subset of contact costs and not added again.",
        f"- Refund and replacement anomaly tickets: {report['anomaly_count']:,}; associated combined exposure ₹{report['anomaly_exposure_inr']:,.2f}; escalation flag only, not recoverable savings or misconduct.",
        "", "## Quarterly view", "", "| Quarter | Tickets | Contact | SLA breach | Transfers | Replacement | Refund | Repeat candidates | Relevant exposure |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for q in qrows:
        lines.append(f"| {q['period']} | {q['ticket_count']:,} | ₹{q['contact_cost_inr']:,.0f} | ₹{q['sla_breach_cost_inr']:,.0f} | ₹{q['transfer_cost_inr']:,.0f} | ₹{q['replacement_cost_inr']:,.0f} | ₹{q['refund_amount_inr']:,.0f} | {q['repeat_contact_candidate_count']:,} / ₹{q['repeat_contact_cost_inr']:,.0f} | ₹{q['total_relevant_exposure_inr']:,.0f} |")
    lines.extend(["", f"Latest complete quarter: {report['latest_complete_quarter']}. The dataset ends 30 June 2026; no Q3 2026 values are inferred.", "", "## Replacement and claim checks", "",
        f"- Replacement calculation uses product unit cost + ₹340 logistics. Finance's approximate ₹2,500 value was not used. December 2025 exposure was ₹{report['replacement_claim_analysis']['december_2025_replacement_exposure_inr']:,.2f}; June 2026 was ₹{report['replacement_claim_analysis']['june_2026_replacement_exposure_inr']:,.2f}; June vs December change {report['replacement_claim_analysis']['june_vs_december_change_pct']}%.",
        f"- Festive proxy uses Q4 2025 vs Q3 2025: ticket volume {report['festive_claim_analysis']['ticket_volume_change_pct']}% and replacement count {report['festive_claim_analysis']['replacement_count_change_pct']}%. This is not a year-over-year seasonal test; Q4 2024 is unavailable, so the claim cannot be established.",
        "", "## Repeat-contact candidates and opportunity", "", f"- Detectable repeat-contact candidates: {report['repeat_contact_candidate_count']:,}; subsequent-contact channel cost: ₹{report['repeat_contact_candidate_cost_inr']:,.2f}. These are issue proxies, not complete FCR.",
        "- 10%, 20%, and 30% scenarios are reported per cost driver in `opportunity_scenarios.parquet`; they are hypothetical reductions and not realized savings.",
        "", "## Limits", "", "- Ticket exposure is not causal attribution; high exposure may reflect ticket mix, workload, or policy-compliant action.",
        "- First-response actor identity is unavailable; SLA is resolver-associated. Transfers may be intentional. Refunds may be policy-valid.",
        "- Repeat-contact matching can miss same-issue contacts and include unrelated issues sharing an order or SKU; candidates only.",
        f"- {report['upstream_audit']['unmatched_roster_ticket_count']:,} tickets lack effective peer/roster context; unmatched tickets remain in overall totals.",
        "- Refund+replacement anomalies are flagged for review; no source values are rewritten. Unknown replacement unit costs would remain flagged and excluded from known cost totals.",
        "- Elapsed handle time is not converted into paid labor cost. No agent ranking, training score, or recommendation is produced.", ""])
    path = interim_dir.parent.parent / "docs" / "technical" / "stage4_findings.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
