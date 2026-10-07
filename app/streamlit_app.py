"""Streamlit presentation layer; all decisions are generated upstream."""
from __future__ import annotations

from pathlib import Path
import logging
import os
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard_data import export_csv, filter_agent_rows, filter_value, load_dashboard_data, resolve_interim_dir, stage7_summary_json
from runtime_health import classify_loaded_dashboard
from vireo import __version__


LOGGER = logging.getLogger("vireo.dashboard")
logging.basicConfig(level=os.environ.get("VIREO_LOG_LEVEL", "INFO").upper(),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
st.set_page_config(page_title="Vireo Support Intelligence", page_icon="📊", layout="wide")


@st.cache_data(show_spinner="Loading validated analysis outputs…")
def _load(root: str, artifact_signature: tuple):
    return load_dashboard_data(root)


def _signature(root: Path) -> tuple:
    interim = resolve_interim_dir(root)
    names = ["training_priority.parquet", "agent_comparison.parquet", "agent_economics.parquet", "agent_metrics.parquet",
             "ai_agent_diagnostics.parquet", "ticket_metrics.parquet", "stage2_metrics_report.json", "stage4_economics_report.json",
             "product_sku_analysis.parquet", "product_family_analysis.parquet", "order_channel_analysis.parquet",
             "product_lot_analysis.parquet", "agent_product_exposure.parquet", "product_order_root_cause_summary.json",
             "stage2_dashboard_summary.json", "stage4_dashboard_summary.json", "stage6_dashboard_summary.json", "stage7_validation_report.json",
             "ai_dashboard_status.json", "stage2_metrics_report.json", "stage4_economics_report.json", "ai_run_report.json"]
    return tuple((name, (interim / name).stat().st_mtime_ns if (interim / name).exists() else None) for name in names)


def _num(value, digits=1):
    return "—" if value is None else f"{value:,.{digits}f}"


def _money(value):
    return "—" if value is None else f"₹{value:,.0f}"


def _root_cause_table(rows):
    frame = pd.DataFrame(rows).copy()
    for field in ("replacement_rate", "share_of_product_tickets", "share_of_agent_tickets"):
        if field in frame:
            frame[field] = frame[field].map(lambda value: f"{value:.1%}" if pd.notna(value) else "—")
    if "replacement_exposure_inr" in frame:
        frame["replacement_exposure_inr"] = frame["replacement_exposure_inr"].map(_money)
    if "mean_csat" in frame:
        frame["mean_csat"] = frame["mean_csat"].map(lambda value: f"{value:.2f}/5" if pd.notna(value) else "—")
    return frame


def _agent_table(rows):
    columns = {
        "agent_id": "Agent ID", "agent_name": "Agent", "agent_team": "Team", "agent_tier": "Tier", "agent_site": "Site", "agent_shift": "Shift",
        "comparison_group": "Peer group", "mean_csat": "CSAT", "csat_gap": "CSAT gap", "handle_time_median": "Median handle time (min)",
        "handle_time_gap": "Handle-time gap (min)", "sla_breach_rate": "SLA breach rate", "sla_gap": "SLA gap",
        "evidence_strength": "Evidence", "stability": "Stability", "priority_status": "Training status",
    }
    frame = pd.DataFrame([{key: row.get(key) for key in columns} for row in rows]).rename(columns=columns)
    if "SLA breach rate" in frame:
        frame["SLA breach rate"] = frame["SLA breach rate"].map(lambda x: f"{x:.1%}" if pd.notna(x) else "—")
    return frame


def _filters(data):
    rows = data["agents"]
    with st.sidebar:
        st.header("Filters")
        query = st.text_input("Search agent", placeholder="Agent ID")
        selections = {}
        for label, field in (("Tier", "agent_tier"), ("Team", "agent_team"), ("Site", "agent_site"), ("Shift", "agent_shift"),
                             ("Training status", "priority_status"), ("Peer group", "comparison_group")):
            options = sorted({filter_value(r.get(field)) for r in rows})
            chosen = st.multiselect(label, options, default=options)
            selections[field] = set(chosen)
    return filter_agent_rows(rows, selections, query)


def _overview(data):
    st.title("Support performance overview")
    first, last = data["available_period"]
    st.caption(f"Available reporting period: {first} → {last} · Latest quarter: {data['latest_quarter'].replace('-', ' ')}")
    m, exposure = data["overall"], data["exposure"]
    cards = [
        ("Tickets", f"{m['ticket_count']:,}"), ("Completed", f"{m['completed_ticket_count']:,}"),
        ("Mean CSAT", _num(m["mean_csat"], 2)), ("CSAT response rate", f"{m['csat_response_rate']:.1%}"),
        ("Median handle time", f"{m['handle_time_median']:,.0f} min"), ("SLA breach rate", f"{m['sla_breach_rate']:.1%}"),
        ("Transfers", f"{m['total_transfers']:,}"), ("Replacement exposure", _money(exposure["replacement_cost_inr"])),
        ("Refund exposure", _money(exposure["refund_amount_inr"])),
    ]
    for start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (label, value) in zip(cols, cards[start:start+3]):
            col.metric(label, value)
    st.subheader("Training status")
    counts = data["priority_counts"]
    candidates = counts.get("training_candidate", 0)
    monitors = counts.get("monitor", 0)
    left, right = st.columns(2)
    left.metric("Training candidates", candidates)
    right.metric("Monitor", monitors)
    if candidates == 0:
        st.info("No agents currently meet the default evidence threshold for a defensible training recommendation.")
        st.caption("Peer-adjusted uncertainty intervals do not establish a clear adverse difference for any agent. Stage 6 therefore does not promote point-estimate differences into training actions.")
    st.caption("Economic figures are observed exposure in the resolved-ticket population, not costs caused by agents or guaranteed savings.")

    st.subheader("Business Goal — proposed operational target")
    goal = (data.get("stage6") or {}).get("business_goal") or {}
    if goal.get("status") == "proposed_operational_target":
        cols = st.columns(3)
        cols[0].metric("Current SLA breach rate", f"{goal['baseline_rate']:.2%}",
                       f"{goal['baseline_breaches']:,}/{goal['eligible_ticket_count']:,} eligible tickets")
        cols[1].metric("Proposed target", f"{goal['target_rate']:.2%}",
                       f"reduce by {goal['target_reduction_percentage_points']:.2f} percentage points")
        cols[2].metric("Policy-credit context", _money(goal["policy_credit_context_same_population_inr"]),
                       f"about {round(goal['expected_fewer_breaches_same_population']):,} fewer breach events on same population")
        st.caption("Analyst-proposed goal; the ₹ figure is a same-population sensitivity using ₹350 per SLA breach under policy. It is not causal attribution, a forecast, realized savings, or guaranteed credits.")
    else:
        st.info("The operational goal is unavailable because the SLA denominator is invalid or absent.")

    st.subheader("Q3 training budget decision")
    budget = (data.get("stage6") or {}).get("training_budget_decision") or {}
    if budget:
        budget_cols = st.columns(3)
        budget_cols[0].metric("Q3 training budget", _money(budget.get("training_budget_inr")))
        budget_cols[1].metric("Agent-specific retraining", _money(budget.get("recommended_agent_specific_allocation_inr")))
        budget_cols[2].metric("Reserve pending stronger evidence", _money(budget.get("reserved_pending_evidence_or_costing_inr")))
        st.caption(budget.get("rationale", "Budget decision aid only."))
        st.caption("Reserved funds are not savings; training costs are unavailable and no ROI is claimed.")
    else:
        st.info("Training budget decision data is unavailable.")

    reviews = data.get("review_lists") or {}
    st.subheader("Bottom 10 — Review Queue")
    st.caption("Lowest peer-adjusted composite point estimates for management review only. This is not a retraining recommendation. Stage 6 status and uncertainty evidence remain separate.")
    bottom = reviews.get("bottom10_review", [])
    st.dataframe(_review_table(bottom), width="stretch", hide_index=True)
    st.subheader("Top 5 — Bonus Review")
    st.caption("Top 5 performance candidates for management review. This view does not determine who deserves a bonus.")
    top = reviews.get("top5_bonus_review", [])
    st.dataframe(_review_table(top), width="stretch", hide_index=True)
    st.caption(reviews.get("definition", "Review scores compare peer-adjusted outcomes and are descriptive only."))


def _review_table(rows):
    fields = [
        ("review_list_rank", "Rank"), ("agent_id", "Agent ID"), ("agent_name", "Agent"),
        ("agent_tier", "Tier"), ("agent_team", "Team"), ("agent_site", "Site"),
        ("review_score", "Peer-adjusted review score"), ("mean_csat", "CSAT"),
        ("peer_mean_csat", "Peer CSAT"), ("completed_ticket_count", "Completed tickets"),
        ("handle_time_mean", "Mean handle time (min)"), ("peer_handle_time_mean", "Peer handle time (min)"),
        ("sla_breach_rate", "SLA breach rate"), ("peer_sla_breach_rate", "Peer SLA breach rate"),
        ("comparison_group", "Peer group"), ("evidence_strength", "Evidence"),
        ("uncertainty", "Uncertainty"), ("priority_status", "Training status"),
    ]
    frame = pd.DataFrame([{label: row.get(key) for key, label in fields} for row in rows],
                         columns=[label for _, label in fields])
    for label in ("SLA breach rate", "Peer SLA breach rate"):
        if label in frame:
            frame[label] = frame[label].map(lambda x: f"{x:.1%}" if pd.notna(x) else "—")
    return frame


def _detail(data):
    st.title("Agent detail")
    ids = [r["agent_id"] for r in data["agents"]]
    selected = st.selectbox("Select agent", ids)
    row = next(r for r in data["agents"] if r["agent_id"] == selected)
    st.subheader(f"{row.get('agent_name') or row['agent_id']} ({row['agent_id']}) · {row.get('agent_team') or 'Team unavailable'} · Tier {row.get('agent_tier') or 'unavailable'}")
    st.write(f"Site: {row.get('agent_site') or 'Unavailable'} · Shift: {row.get('agent_shift') or 'Unavailable'} · Peer group: {row.get('comparison_group') or 'Unavailable'}")

    st.markdown("#### Performance and peer comparison")
    metrics = [
        ("CSAT", row.get("mean_csat"), row.get("peer_mean_csat"), row.get("csat_gap")),
        ("Handle time mean (min)", row.get("raw_handle_time_mean"), row.get("peer_handle_time_mean"), row.get("handle_time_gap")),
        ("SLA breach rate", row.get("sla_breach_rate"), row.get("peer_sla_breach_rate"), row.get("sla_gap")),
    ]
    for label, own, peer, gap in metrics:
        own_text = f"{own:.1%}" if label == "SLA breach rate" and own is not None else _num(own, 2)
        peer_text = f"{peer:.1%}" if label == "SLA breach rate" and peer is not None else _num(peer, 2)
        gap_text = f"{gap:+.1%}" if label == "SLA breach rate" and gap is not None else (f"{gap:+.2f}" if gap is not None else "—")
        st.write(f"**{label}:** agent {own_text} · peer {peer_text} · gap {gap_text}")
    st.caption(f"Completed tickets: {row.get('completed_ticket_count', 0):,} · CSAT responses: {row.get('csat_completed_response_count', 0):,} · Median handle time: {_num(row.get('handle_time_median'), 0)} min · SLA breaches: {row.get('sla_breach_count', 0):,}/{row.get('sla_eligible_count', 0):,}")

    st.markdown("#### Evidence and decision")
    stability = row.get("stability")
    stability_label = stability.get("state", "Unavailable") if isinstance(stability, dict) else (stability or "Unavailable")
    st.write(f"**Status:** {row.get('priority_status')} · **Evidence:** {row.get('evidence_strength')} · **Stability:** {stability_label} · **Uncertainty:** {row.get('uncertainty')}")
    st.write(f"**Sample size:** {row.get('sample_size')} · **Other peer agents:** {row.get('peer_agent_count')} · **Peer-context coverage:** {row.get('roster_coverage'):.1%}" if row.get("roster_coverage") is not None else f"**Sample size:** {row.get('sample_size')} · **Other peer agents:** {row.get('peer_agent_count')}")
    explanation = row.get("explanation")
    explanation_text = explanation.get("why") if isinstance(explanation, dict) else explanation
    st.info(explanation_text or row.get("priority_reason") or "No structured explanation is available.")
    for limitation in row.get("limitations") or []:
        st.caption(f"• {limitation}")
    cited = row.get("representative_ticket_ids") or []
    st.caption("Supporting ticket IDs: " + (", ".join(cited) if cited else "None available in validated Stage 6 evidence."))

    st.markdown("#### AI diagnostics")
    ai = row.get("ai_diagnostics")
    if not ai or not ai.get("themes"):
        st.info("AI diagnostics unavailable. No validated real-model diagnostic evidence is available for this run.")
    else:
        st.write("AI themes are unvalidated diagnostic context and do not change numeric decisions.")
        st.write(ai.get("themes"))
        st.write("Representative ticket IDs:", ", ".join(ai.get("representative_ticket_ids") or []))

    st.markdown("#### Economic context")
    st.caption("Observed exposure associated with this agent's resolved-ticket population. This is not cost caused by the agent.")
    econ_cols = st.columns(4)
    for col, (label, field) in zip(econ_cols, (("Operational", "operational_cost_exposure_inr"), ("Transfer", "internal_transfer_cost_exposure_inr"), ("Replacement", "replacement_exposure_inr"), ("Refund", "refund_exposure_inr"))):
        col.metric(label, _money(row.get(field)))
    st.caption("Exposure includes different accounting categories and does not imply avoidable cost or guaranteed savings.")


def _trust(data):
    st.title("Methodology and trust")
    st.markdown("""
### How to read the measures
- **CSAT:** mean valid 1–5 score on resolved or closed tickets. Open/pending scores are excluded from the primary measure.
- **Handle time:** elapsed time from first response to resolution, for completed tickets with valid timestamps. The median is shown because the distribution contains extreme values; the underlying analysis retains valid outliers.
- **SLA:** share of tickets whose first response exceeded the channel-specific policy target. The source identifies the resolver, not the first responder, so agent SLA values are resolver-associated outcomes.
- **Peer comparison:** comparisons use effective roster context and observed case mix. Tier 1 and Tier 2 are kept separate; sparse groups can fall back to broader Tier-safe peers.
- **Uncertainty:** a point difference alone is not sufficient. The default decision engine requires an adjusted interval wholly in the adverse direction, sufficient evidence, coverage, and a supported peer group.
- **Training priority:** deterministic Stage 6 output. Economic exposure and AI evidence do not affect its numeric score. The current run returns zero candidates and 44 monitors.
- **Economics:** Stage 4 reports observed contact, breach, transfer, replacement, refund, and related exposure. Hypothetical scenario opportunity is not guaranteed savings and is not attributed causally to an agent.
- **AI:** Stage 5 is partial. The current run has no real provider predictions, model quality evaluation, or real usage cost. The deterministic dashboard remains usable without AI.
- **Review queues:** Bottom 10 and Top 5 order only peer-supported agents using a fixed-scale composite of Tier-safe, case-mix-adjusted gaps. They are management review lists, not training or bonus decisions; evidence and uncertainty remain visible.
- **Business goal:** The proposed goal is a 1 percentage-point reduction in the observed resolver-associated SLA breach rate. Its policy-credit context applies ₹350 per breach to the same observed ticket denominator and is a sensitivity, not a forecast or savings claim.
- **Q3 training budget:** With zero evidence-gated training candidates and no training-cost data, the current decision is ₹0 for agent-specific retraining and reserve the ₹4,00,000 pending stronger evidence or targeted process investigation.

> The system identifies evidence-based training candidates; it does not establish that an agent caused a customer or financial outcome.

### Known limitations
Stage 3 intervals are approximate and assume independent tickets. Clustered case-mix uncertainty and genuine out-of-time validation are not implemented. There is no real-world ground truth for decision error rates. There are 567 tickets without effective roster context. Handle-time outliers remain in calculations. SLA is associated with the resolver because first-responder identity is unavailable. Legacy timestamp provenance and some source anomalies remain documented in the forensic report.
""")
    if data.get("stage7"):
        st.markdown("### Stage 7 validation")
        st.write(f"Report status: **{data['stage7'].get('status')}** · readiness: **{data['stage7'].get('production_readiness_verdict')}**")
        st.download_button("Download Stage 7 validation summary", stage7_summary_json(data["stage7"]), "stage7_validation_summary.json", "application/json")


def _product_orders(data):
    st.title("Product & Orders — descriptive root-cause analysis")
    root = data.get("root_cause") or {}
    summary = root.get("summary")
    if not summary:
        st.info("Product/order analysis is unavailable in this dashboard bundle. Regenerate Stage 4 outputs and the reduced dashboard bundle to include it.")
        return
    counts = summary["order_match_counts"]
    st.caption("Observed associations only. This page does not establish product causality, agent fault, avoidable cost, or training recommendations.")
    a, b, c, d = st.columns(4)
    a.metric("Tickets", f"{summary['ticket_count']:,}")
    b.metric("Orders matched", f"{counts['matched']:,} ({summary['order_match_rate']:.1%})")
    c.metric("Ambiguous", f"{counts['ambiguous']:,}")
    d.metric("Unmatched", f"{counts['unmatched']:,}")
    st.info(f"Order association preserves one row per ticket. Minimum support: {summary['minimum_support']} replacement-eligible tickets. {summary['minimum_support_definition']}")

    pl2 = summary.get("va_eb_pl2")
    comparison = summary.get("va_eb_pl2_comparison") or {}
    if pl2 and pl2.get("replacement_rate") is not None and pl2["replacement_rate"] > (comparison.get("other_sku_replacement_rate") or 0):
        csat = "unavailable" if pl2.get("mean_csat") is None else f"{pl2['mean_csat']:.2f}/5 from {pl2['csat_response_count']:,} responses"
        st.subheader("Key descriptive signal")
        st.write(f"**VA-EB-PL2:** {pl2['replacement_count']:,}/{pl2['replacement_eligible_count']:,} eligible tickets had replacements ({pl2['replacement_rate']:.1%}); observed replacement exposure {_money(pl2['replacement_exposure_inr'])}; completed-ticket CSAT {csat}.")
        rate = comparison.get("other_sku_replacement_rate")
        other_csat = comparison.get("other_sku_mean_csat")
        st.write(f"Other SKUs: {comparison['other_sku_replacement_count']:,}/{comparison['other_sku_replacement_eligible_count']:,} ({rate:.1%}) and mean CSAT {other_csat:.2f}/5 from {comparison['other_sku_csat_response_count']:,} responses." if rate is not None and other_csat is not None else "The other-SKU comparison is incomplete.")
        st.caption("This signal supports an operational product/order investigation; it does not establish that the product caused the outcomes.")

    st.subheader("Product / SKU")
    st.dataframe(_root_cause_table(root.get("product_sku", [])), width="stretch", hide_index=True)
    st.subheader("Product family")
    families = root.get("product_family", [])
    if families:
        family_columns = {
            "product_family": "Product family",
            "ticket_count": "Ticket count",
            "completed_ticket_count": "Completed tickets",
            "replacement_eligible_count": "Eligible tickets",
            "replacement_count": "Replacement count",
            "replacement_rate": "Replacement rate",
            "replacement_exposure_inr": "Replacement exposure",
            "csat_response_count": "CSAT responses",
            "mean_csat": "Mean CSAT",
        }
        family_table = _root_cause_table(families).rename(columns=family_columns)
        st.dataframe(family_table.reindex(columns=list(family_columns.values())), width="stretch", hide_index=True)
    else:
        st.info("Product-family analysis is unavailable in this dashboard bundle.")
    st.subheader("Order channel")
    channels = root.get("order_channel", [])
    if channels:
        st.dataframe(_root_cause_table(channels), width="stretch", hide_index=True)
    else:
        st.info("No matched tickets have usable order-channel values.")
    st.subheader("Manufacturing lots")
    if summary.get("lot_status") == "supported" and root.get("lot"):
        st.dataframe(_root_cause_table(root["lot"]), width="stretch", hide_index=True)
    else:
        st.info(f"Lot analysis: NOT RELIABLE. {summary.get('lot_reason')}")
    st.subheader("Agent exposure to products")
    st.caption("Combinations below the support floor remain visible with a support label; these rows are descriptive exposure context and are not agent rankings.")
    agent_signal = summary.get("va_eb_pl2_agent_exposure") or {}
    if agent_signal.get("supported_agent_count"):
        st.write(f"VA-EB-PL2 exposure is broad: {agent_signal['supported_agent_count']} of {agent_signal['total_agents']} agents handled at least {summary['minimum_support']} eligible cases. Within-SKU replacement rates range from {agent_signal['replacement_rate_min']:.1%} to {agent_signal['replacement_rate_max']:.1%} across {agent_signal['ticket_count_min']}–{agent_signal['ticket_count_max']} tickets per agent. These unadjusted differences need case and policy review; they do not establish agent fault.")
    st.dataframe(_root_cause_table(root.get("agent_product", [])), width="stretch", hide_index=True)
    st.caption("Rates use replacement-eligible Y/N ticket flags. CSAT means use completed tickets with valid CSAT; response counts are shown. Exposures are observed ticket-associated policy costs, not agent-caused costs or savings.")


def main():
    st.sidebar.title("Vireo Support Intelligence")
    st.sidebar.caption(f"Version {__version__}")
    if not st.session_state.get("vireo_startup_logged"):
        LOGGER.info("Application startup version=%s ai_mode=optional_offline", __version__)
        st.session_state["vireo_startup_logged"] = True
    try:
        data = _load(str(ROOT), _signature(ROOT))
    except Exception as exc:
        LOGGER.exception("Required dashboard outputs failed startup validation")
        LOGGER.error("Health state=unhealthy")
        st.error(f"Analysis outputs could not be loaded: {exc}")
        st.info("Supply a valid dashboard data bundle in the configured output directory, then reload this page.")
        st.stop()
    health = classify_loaded_dashboard(data)
    LOGGER.info("Dashboard data loaded agents=%d health=%s ai_status=%s", len(data["agents"]), health["status"], health["ai_status"])

    pages = ["Overview", "Agents", "Agent Detail"]
    if (data.get("root_cause") or {}).get("summary"):
        pages.append("Product & Orders")
    pages.append("Methodology / Trust")
    page = st.sidebar.radio("Navigate", pages)
    try:
        if page == "Overview":
            _overview(data)
        elif page == "Agents":
            rows = _filters(data)
            st.title("Agents")
            st.caption("Raw performance is descriptive; peer-adjusted gaps compare agents with supported peers; training status is the decision engine output. Review queues on Overview are descriptive and do not change training status.")
            view = st.radio("View", ["Peer-adjusted performance", "Raw performance", "Training priority"], horizontal=True)
            if view == "Raw performance":
                frame = pd.DataFrame([{"Agent":r["agent_id"],"Team":r.get("agent_team"),"Tier":r.get("agent_tier"),"Site":r.get("agent_site"),"Shift":r.get("agent_shift"),"Tickets":r.get("ticket_count"),"CSAT":r.get("mean_csat"),"Median handle time (min)":r.get("handle_time_median"),"SLA breach rate":f"{r['sla_breach_rate']:.1%}" if r.get("sla_breach_rate") is not None else "—","Training status":r.get("priority_status")} for r in rows])
            elif view == "Training priority":
                frame = pd.DataFrame([{"Agent":r["agent_id"],"Status":r.get("priority_status"),"Band":r.get("priority_band"),"Score":r.get("priority_score"),"Decision rank":r.get("priority_rank"),"Evidence":r.get("evidence_strength"),"Stability":r.get("stability"),"Uncertainty":r.get("uncertainty"),"Decision explanation":r.get("priority_reason")} for r in rows])
            else:
                frame = _agent_table(rows)
            st.dataframe(frame, width="stretch", hide_index=True)
            st.caption(f"{len(rows)} agents match the selected filters. Priority rank and score, when present, come directly from Stage 6.")
            st.download_button("Download training_priority.csv", export_csv(rows, "training_priority"), "training_priority.csv", "text/csv")
            st.download_button("Download agent_performance.csv", export_csv(rows, "agent_performance"), "agent_performance.csv", "text/csv")
            st.download_button("Download agent_economics.csv", export_csv(rows, "agent_economics"), "agent_economics.csv", "text/csv")
        elif page == "Agent Detail":
            _detail(data)
        elif page == "Product & Orders":
            _product_orders(data)
        else:
            _trust(data)
    except Exception:
        LOGGER.exception("Unexpected dashboard page error")
        st.error("This dashboard page could not be rendered. Check application logs and the deployment data bundle.")


if __name__ == "__main__":
    main()
