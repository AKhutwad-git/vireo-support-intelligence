"""Bounded, deterministic ticket-to-order/product descriptive analysis."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


MINIMUM_SUPPORT = 30


def _text(value):
    return str(value).strip() if value not in (None, "") else None


def _number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_map(rows, key):
    result = {}
    for row in rows:
        value = row.get(key)
        if value in (None, "") or value in result:
            raise ValueError(f"{key} values must be present and unique")
        result[value] = row
    return result


def enrich_tickets_with_orders(ticket_metrics: list[dict], orders: list[dict], products: list[dict],
                               ticket_economics: list[dict]) -> list[dict]:
    """Return one row per ticket; unresolved/conflicting order evidence stays unresolved."""
    ticket_by_id = _safe_map(ticket_metrics, "ticket_id")
    economics_by_id = _safe_map(ticket_economics, "ticket_id")
    if set(ticket_by_id) != set(economics_by_id):
        raise ValueError("Ticket metrics and economics IDs do not reconcile")
    order_by_id = _safe_map(orders, "order_id")
    product_by_sku = _safe_map(products, "sku")
    fallback = defaultdict(list)
    for order in orders:
        customer, sku = _text(order.get("customer_id")), _text(order.get("sku"))
        if customer and sku:
            fallback[(customer, sku)].append(order)

    result = []
    for ticket_id, ticket in ticket_by_id.items():
        source_order_id = _text(ticket.get("order_id"))
        customer, sku = _text(ticket.get("customer_id")), _text(ticket.get("product_sku"))
        order, method, status = None, None, "unmatched"
        if source_order_id and source_order_id in order_by_id:
            candidate = order_by_id[source_order_id]
            evidence_agrees = ((not customer or _text(candidate.get("customer_id")) == customer)
                               and (not sku or _text(candidate.get("sku")) == sku))
            if evidence_agrees and (customer or sku):
                order, method, status = candidate, "direct_order_id", "matched"
            else:
                status = "ambiguous"
                method = "conflicting_direct_order_id"
        else:
            candidates = fallback.get((customer, sku), []) if customer and sku else []
            if len(candidates) == 1:
                order, method, status = candidates[0], "unique_customer_sku", "matched"
            elif len(candidates) > 1:
                status, method = "ambiguous", "multiple_customer_sku_orders"

        economics = economics_by_id[ticket_id]
        product = product_by_sku.get(sku) if sku else None
        completed = bool(ticket.get("attendance_flag"))
        csat = _number(ticket.get("csat_score_numeric"))
        csat_valid = completed and bool(ticket.get("valid_for_csat")) and csat is not None
        replacement_value = _text(ticket.get("replacement_issued"))
        replacement_eligible = replacement_value is not None and replacement_value.upper() in {"Y", "N"}
        replacement = replacement_eligible and replacement_value.upper() == "Y"
        exposure = _number(economics.get("replacement_exposure_inr")) or 0.0
        result.append({
            "ticket_id": ticket_id, "customer_id": customer, "order_id": _text(order.get("order_id")) if order else None,
            "source_order_id": source_order_id, "order_match_status": status, "order_match_method": method,
            "order_channel": _text(order.get("channel")) if order else None,
            "order_lot_code": _text(order.get("lot_code")) if order else None,
            "order_date": _text(order.get("order_date")) if order else None,
            "order_quantity": _number(order.get("qty")) if order else None,
            "order_value_inr": _number(order.get("order_value_inr")) if order else None,
            "product_sku": sku, "product_name": product.get("product_name") if product else None,
            "product_family": product.get("family") if product else None,
            "warranty_months": _number(product.get("warranty_months")) if product else None,
            "agent_id": _text(ticket.get("agent_id")), "completed": completed,
            "replacement_eligible": replacement_eligible, "replacement": replacement,
            "replacement_exposure_inr": exposure, "csat_valid": csat_valid,
            "csat_score": csat if csat_valid else None,
        })
    if len(result) != len(ticket_metrics) or len({row["ticket_id"] for row in result}) != len(result):
        raise ValueError("Ticket-to-order enrichment changed ticket grain")
    return result


def _aggregate(rows: list[dict], keys: tuple[str, ...], minimum_support: int = MINIMUM_SUPPORT) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = tuple(row.get(field) for field in keys)
        groups[key].append(row)
    output = []
    for key, values in sorted(groups.items(), key=lambda item: str(item[0])):
        eligible = sum(row["replacement_eligible"] for row in values)
        replacements = sum(row["replacement"] for row in values)
        csat_values = [row["csat_score"] for row in values if row["csat_valid"]]
        ticket_count = len(values)
        item = dict(zip(keys, key))
        item.update({
            "ticket_count": ticket_count,
            "completed_ticket_count": sum(row["completed"] for row in values),
            "replacement_eligible_count": eligible,
            "replacement_count": replacements,
            "replacement_rate": replacements / eligible if eligible else None,
            "replacement_exposure_inr": round(sum(row["replacement_exposure_inr"] for row in values), 2),
            "csat_response_count": len(csat_values),
            "mean_csat": sum(csat_values) / len(csat_values) if csat_values else None,
            "support_status": "supported" if eligible >= minimum_support else "below_minimum_support",
        })
        output.append(item)
    return output


def build_product_order_analysis(ticket_metrics: list[dict], orders: list[dict], products: list[dict],
                                 ticket_economics: list[dict], minimum_support: int = MINIMUM_SUPPORT) -> dict[str, Any]:
    if minimum_support < 1:
        raise ValueError("minimum_support must be positive")
    enriched = enrich_tickets_with_orders(ticket_metrics, orders, products, ticket_economics)
    sku = _aggregate([row for row in enriched if row.get("product_sku")], ("product_sku", "product_name", "product_family"), minimum_support)
    family = _aggregate([row for row in enriched if row.get("product_family")], ("product_family",), minimum_support)
    channel_rows = _aggregate([row for row in enriched if row["order_match_status"] == "matched" and row.get("order_channel")], ("order_channel",), minimum_support)
    lot_rows_all = _aggregate([row for row in enriched if row["order_match_status"] == "matched" and row.get("order_lot_code")],
                              ("product_sku", "product_name", "product_family", "order_lot_code"), minimum_support)
    lots = [row for row in lot_rows_all if row["replacement_eligible_count"] >= minimum_support]
    agent_product = _aggregate([row for row in enriched if row.get("agent_id") and row.get("product_sku")], ("agent_id", "product_sku", "product_name", "product_family"), minimum_support)
    sku_counts = {row["product_sku"]: row["ticket_count"] for row in sku}
    agent_counts = defaultdict(int)
    for row in enriched:
        if row.get("agent_id"):
            agent_counts[row["agent_id"]] += 1
    for row in agent_product:
        row["product_ticket_count"] = sku_counts.get(row["product_sku"], 0)
        row["share_of_product_tickets"] = row["ticket_count"] / row["product_ticket_count"] if row["product_ticket_count"] else None
        row["agent_ticket_count"] = agent_counts[row["agent_id"]]
        row["share_of_agent_tickets"] = row["ticket_count"] / row["agent_ticket_count"] if row["agent_ticket_count"] else None
    sku_sorted = sorted((row for row in sku if row["replacement_eligible_count"] >= minimum_support),
                        key=lambda row: (-(row["replacement_rate"] or 0), row["product_sku"]))
    exposure_sorted = sorted(sku, key=lambda row: (-row["replacement_exposure_inr"], row["product_sku"]))
    csat_sorted = sorted((row for row in sku if row["csat_response_count"] >= minimum_support),
                         key=lambda row: (row["mean_csat"] if row["mean_csat"] is not None else 999, row["product_sku"]))
    pl2 = next((row for row in sku if row["product_sku"] == "VA-EB-PL2"), None)
    others = [row for row in enriched if row.get("product_sku") != "VA-EB-PL2"]
    others_eligible = sum(row["replacement_eligible"] for row in others)
    others_replacements = sum(row["replacement"] for row in others)
    other_csat = [row["csat_score"] for row in others if row["csat_valid"]]
    statuses = {status: sum(row["order_match_status"] == status for row in enriched)
                for status in ("matched", "ambiguous", "unmatched")}
    pl2_agent_rows = [row for row in agent_product if row["product_sku"] == "VA-EB-PL2"
                      and row["replacement_eligible_count"] >= minimum_support]
    matched_replacements = sum(row["replacement"] for row in enriched if row["order_match_status"] == "matched")
    replacement_total = sum(row["replacement"] for row in enriched)
    summary = {
        "ticket_count": len(enriched), "distinct_ticket_ids": len({row["ticket_id"] for row in enriched}),
        "rows_before": len(ticket_metrics), "rows_after": len(enriched), "row_count_preserved": len(ticket_metrics) == len(enriched),
        "order_match_counts": statuses, "order_match_rate": statuses["matched"] / len(enriched) if enriched else None,
        "replacement_count": replacement_total,
        "replacement_order_match_coverage": matched_replacements / replacement_total if replacement_total else None,
        "minimum_support": minimum_support,
        "minimum_support_definition": f"At least {minimum_support} eligible tickets for replacement-rate display; CSAT means show their response denominator, and no significance is implied.",
        "replacement_rate_definition": "replacement tickets / tickets with a recorded Y or N replacement flag",
        "csat_definition": "Mean CSAT among completed tickets with valid_for_csat=true and a numeric score; denominator is csat_response_count.",
        "lot_status": "supported" if lots else "NOT RELIABLE",
        "lot_reason": None if lots else f"No lot has at least {minimum_support} replacement-eligible matched tickets; lot-level rates are suppressed.",
        "lot_supported_count": len(lots), "lot_below_support_count": len(lot_rows_all) - len(lots),
        "top_replacement_rate_skus": sku_sorted[:5], "top_replacement_exposure_skus": exposure_sorted[:5],
        "lowest_csat_supported_skus": csat_sorted[:5],
        "va_eb_pl2": pl2,
        "va_eb_pl2_comparison": {
            "other_sku_ticket_count": len(others), "other_sku_replacement_eligible_count": others_eligible,
            "other_sku_replacement_count": others_replacements,
            "other_sku_replacement_rate": others_replacements / others_eligible if others_eligible else None,
            "other_sku_replacement_exposure_inr": round(sum(row["replacement_exposure_inr"] for row in others), 2),
            "other_sku_csat_response_count": len(other_csat),
            "other_sku_mean_csat": sum(other_csat) / len(other_csat) if other_csat else None,
        },
        "agent_product_supported_rows": sum(row["replacement_eligible_count"] >= minimum_support for row in agent_product),
        "va_eb_pl2_agent_exposure": {
            "supported_agent_count": len(pl2_agent_rows),
            "total_agents": len(agent_counts),
            "ticket_count_min": min((row["ticket_count"] for row in pl2_agent_rows), default=None),
            "ticket_count_max": max((row["ticket_count"] for row in pl2_agent_rows), default=None),
            "replacement_rate_min": min((row["replacement_rate"] for row in pl2_agent_rows), default=None),
            "replacement_rate_max": max((row["replacement_rate"] for row in pl2_agent_rows), default=None),
            "max_share_of_product_tickets": max((row["share_of_product_tickets"] for row in pl2_agent_rows), default=None),
            "definition": f"Agent-product combinations with at least {minimum_support} replacement-eligible tickets; descriptive only, no case-mix adjustment or significance test.",
        },
        "interpretation": "Descriptive associations only. Product/order patterns may reflect allocation, customer mix, policy, or other factors; they do not establish product causality or agent fault and do not feed training decisions.",
    }
    return {"enriched": enriched, "product_sku": sku, "product_family": family,
            "order_channel": channel_rows, "lot": lots, "agent_product": agent_product,
            "summary": summary, "lot_all": lot_rows_all}


def _markdown(analysis: dict[str, Any]) -> str:
    summary = analysis["summary"]
    def pct(value):
        return "—" if value is None else f"{value:.1%}"
    def money(value):
        return f"₹{value:,.0f}"
    lines = ["# Product and Order Root-Cause Analysis", "", "## Scope", "",
             f"- Ticket population: {summary['ticket_count']:,}; rows preserved: {summary['row_count_preserved']}.",
             f"- Order links: {summary['order_match_counts']['matched']:,} matched ({pct(summary['order_match_rate'])}), {summary['order_match_counts']['ambiguous']:,} ambiguous, {summary['order_match_counts']['unmatched']:,} unmatched.",
             f"- Replacements: {summary['replacement_count']:,}; {pct(summary['replacement_order_match_coverage'])} link to a matched order.",
             f"- Minimum support: {summary['minimum_support_definition']}", "",
             "## Product/SKU findings", "", "Observed SKU aggregates; rates use eligible Y/N flags and CSAT means use completed valid responses.", "",
             "| SKU | Tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in summary["top_replacement_rate_skus"]:
        mean_csat = "—" if row["mean_csat"] is None else f"{row['mean_csat']:.2f}"
        lines.append(f"| {row['product_sku']} | {row['ticket_count']:,} | {row['replacement_eligible_count']:,} | {row['replacement_count']:,} | {pct(row['replacement_rate'])} | {money(row['replacement_exposure_inr'])} | {row['csat_response_count']:,} | {mean_csat} |")
    lines.extend(["", "### Replacement exposure leaders", "", "| SKU | Tickets | Replacements | Exposure |", "|---|---:|---:|---:|"])
    for row in summary["top_replacement_exposure_skus"]:
        lines.append(f"| {row['product_sku']} | {row['ticket_count']:,} | {row['replacement_count']:,} | {money(row['replacement_exposure_inr'])} |")
    lines.extend(["", "### VA-EB-PL2 check", ""])
    row = summary.get("va_eb_pl2")
    comp = summary["va_eb_pl2_comparison"]
    if row:
        lines.append(f"Observed VA-EB-PL2: {row['ticket_count']:,} tickets; {row['replacement_eligible_count']:,} eligible; {row['replacement_count']:,} replacements ({pct(row['replacement_rate'])}); {money(row['replacement_exposure_inr'])} exposure; {row['csat_response_count']:,} completed valid CSAT responses; mean {row['mean_csat']:.2f}/5.")
        lines.append(f"Other SKUs: {comp['other_sku_ticket_count']:,} tickets; {comp['other_sku_replacement_eligible_count']:,} eligible; {comp['other_sku_replacement_count']:,} replacements ({pct(comp['other_sku_replacement_rate'])}); {money(comp['other_sku_replacement_exposure_inr'])} exposure; {comp['other_sku_csat_response_count']:,} valid CSAT responses; mean {comp['other_sku_mean_csat']:.2f}/5.")
    else:
        lines.append("VA-EB-PL2 does not appear in the canonical product/ticket data.")
    lines.extend(["", "## Order-channel findings", "", "| Order channel | Tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for item in analysis["order_channel"]:
        mean_csat = "—" if item["mean_csat"] is None else f"{item['mean_csat']:.2f}"
        lines.append(f"| {item['order_channel']} | {item['ticket_count']:,} | {item['replacement_eligible_count']:,} | {item['replacement_count']:,} | {pct(item['replacement_rate'])} | {money(item['replacement_exposure_inr'])} | {item['csat_response_count']:,} | {mean_csat} |")
    lines.extend(["", "## Lot findings", ""])
    if analysis["lot"]:
        lines.append(f"{len(analysis['lot']):,} lots meet the {summary['minimum_support']} eligible-ticket floor; {summary['lot_below_support_count']:,} additional observed SKU-lot groups are below that floor and omitted from rate comparisons. Lot rates are descriptive and do not imply manufacturing causality.")
        lines.extend(["", "| SKU | Lot | Tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"])
        for item in sorted(analysis["lot"], key=lambda row: (-row["replacement_rate"], row["order_lot_code"]))[:10]:
            mean_csat = "—" if item["mean_csat"] is None else f"{item['mean_csat']:.2f}"
            lines.append(f"| {item['product_sku']} | {item['order_lot_code']} | {item['ticket_count']:,} | {item['replacement_eligible_count']:,} | {item['replacement_count']:,} | {pct(item['replacement_rate'])} | {money(item['replacement_exposure_inr'])} | {item['csat_response_count']:,} | {mean_csat} |")
    else:
        lines.append(f"Lot analysis: NOT RELIABLE. {summary['lot_reason']}")
    lines.extend(["", "## Agent exposure", "", f"{summary['agent_product_supported_rows']:,} agent-product combinations meet the {summary['minimum_support']} eligible-ticket floor. The table is exposure context only; it is not an agent ranking or training input.", "", "| Agent | SKU | Tickets | Share of SKU tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
    major = {row["product_sku"] for row in summary["top_replacement_exposure_skus"]}
    exposures = [row for row in analysis["agent_product"] if row["product_sku"] in major and row["replacement_eligible_count"] >= summary["minimum_support"]]
    for item in sorted(exposures, key=lambda row: (-row["replacement_exposure_inr"], row["agent_id"], row["product_sku"]))[:20]:
        mean_csat = "—" if item["mean_csat"] is None else f"{item['mean_csat']:.2f}"
        lines.append(f"| {item['agent_id']} | {item['product_sku']} | {item['ticket_count']:,} | {pct(item['share_of_product_tickets'])} | {item['replacement_eligible_count']:,} | {item['replacement_count']:,} | {pct(item['replacement_rate'])} | {money(item['replacement_exposure_inr'])} | {item['csat_response_count']:,} | {mean_csat} |")
    agent_signal = summary["va_eb_pl2_agent_exposure"]
    if agent_signal["supported_agent_count"]:
        lines.extend(["", f"Across agents, {agent_signal['supported_agent_count']} of {agent_signal['total_agents']} handled at least {summary['minimum_support']} eligible VA-EB-PL2 tickets. Their observed within-SKU replacement rates range from {pct(agent_signal['replacement_rate_min'])} to {pct(agent_signal['replacement_rate_max'])} over {agent_signal['ticket_count_min']}–{agent_signal['ticket_count_max']} tickets; the largest individual share is {pct(agent_signal['max_share_of_product_tickets'])} of PL2 tickets. These unadjusted differences require case and policy review and do not establish agent fault."])
    lines.extend(["", "## Interpretation", "", "**Observed:** product, order-channel, lot, and agent-product differences are measurable in this supplied population using the denominators above.", "", "**Possible explanation:** the PL2 SKU/lot pattern is a strong operational investigation lead, while the broadly distributed product exposure and within-SKU differences indicate product mix alone may not explain every agent outcome. Review product/lot evidence and ticket handling before making agent-specific decisions.", "", "**Not established:** causality, product defects, agent fault, avoidable costs, or guaranteed savings. The analysis does not alter peer comparisons or training decisions.", "", "## Reproducible artifacts", "", "- `data/outputs/product_order_root_cause.csv`: combined SKU, family, order-channel, supported lot, and agent-product aggregates.", "- `data/interim/ticket_order_enriched.parquet`: internal one-row-per-ticket linkage and flags; it is not included in dashboard bundles.", "- `data/interim/product_order_root_cause_summary.json` and the Stage 4 report: coverage, definitions, support thresholds, and aggregate outputs.", "- `data/interim/product_sku_analysis.parquet`, `product_family_analysis.parquet`, `order_channel_analysis.parquet`, `product_lot_analysis.parquet`, and `agent_product_exposure.parquet`: dashboard aggregate tables.", ""])
    return "\n".join(lines)


def write_product_order_analysis(interim_dir: Path, analysis: dict[str, Any]) -> dict[str, Any]:
    interim_dir = Path(interim_dir)
    outputs = {"product_sku_analysis": analysis["product_sku"], "product_family_analysis": analysis["product_family"],
               "order_channel_analysis": analysis["order_channel"], "product_lot_analysis": analysis["lot"],
               "agent_product_exposure": analysis["agent_product"],
               "ticket_order_enriched": analysis["enriched"]}
    for name, rows in outputs.items():
        pq.write_table(pa.Table.from_pylist(rows) if rows else pa.table({}), interim_dir / f"{name}.parquet", compression="zstd")
    csv_rows = []
    for level, rows, key in (("product_sku", analysis["product_sku"], "product_sku"),
                             ("product_family", analysis["product_family"], "product_family"),
                             ("order_channel", analysis["order_channel"], "order_channel"),
                             ("lot", analysis["lot"], "order_lot_code")):
        for row in rows:
            csv_rows.append({"analysis_level": level, "dimension": row.get(key), "product_sku": row.get("product_sku"), **{field: row.get(field) for field in (
                "ticket_count", "completed_ticket_count", "replacement_eligible_count", "replacement_count", "replacement_rate",
                "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status")}})
    for row in analysis["agent_product"]:
        csv_rows.append({"analysis_level": "agent_product", "dimension": row.get("product_sku"),
                         "product_sku": row.get("product_sku"), "agent_id": row.get("agent_id"), **{field: row.get(field) for field in (
                "ticket_count", "completed_ticket_count", "replacement_eligible_count", "replacement_count", "replacement_rate",
                "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status")}})
    csv_path = interim_dir.parent.parent / "data" / "outputs" / "product_order_root_cause.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["analysis_level", "dimension", "product_sku", "agent_id", "ticket_count", "completed_ticket_count", "replacement_eligible_count",
                  "replacement_count", "replacement_rate", "replacement_exposure_inr", "csat_response_count", "mean_csat", "support_status"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)
    analysis["summary"]["outputs"] = {name: {"path": f"data/interim/{name}.parquet", "row_count": len(rows)} for name, rows in outputs.items()}
    analysis["summary"]["outputs"]["product_order_root_cause.csv"] = {"path": "data/outputs/product_order_root_cause.csv", "row_count": len(csv_rows)}
    analysis["summary"]["outputs"]["product_order_root_cause_analysis.md"] = {"path": "docs/technical/product_order_root_cause_analysis.md"}
    import json
    (interim_dir / "product_order_root_cause_summary.json").write_text(json.dumps(analysis["summary"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    doc = interim_dir.parent.parent / "docs" / "technical" / "product_order_root_cause_analysis.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(_markdown(analysis), encoding="utf-8", newline="\n")
    return analysis["summary"]
