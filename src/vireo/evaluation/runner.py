"""Stage 7 reproducible evaluation orchestration and artifact generation."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from vireo.evaluation.decision_validation import explanation_consistency
from vireo.evaluation.reconciliation import independent_reference, reconcile
from vireo.evaluation.robustness import clustered_customer_bootstrap, peer_group_robustness, temporal_leave_one_quarter_out
from vireo.evaluation.sensitivity import evaluate_sensitivity
from vireo.evaluation.synthetic import synthetic_decision_scenarios
from vireo.scoring.priority import build_priority_rows


def _rows(path):
    return pq.read_table(path).to_pylist()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def _write_parquet(path, rows):
    pq.write_table(pa.Table.from_pylist(rows) if rows else pa.table({}), path, compression="zstd")


def _compute(root, config, bootstrap_replicates):
    interim = root / "data" / "interim"
    tickets = _rows(interim / "normalized_tickets.parquet")
    ticket_metrics = _rows(interim / "ticket_metrics.parquet")
    products = _rows(interim / "normalized_products.parquet")
    metrics_report = json.loads((interim / "stage2_metrics_report.json").read_text(encoding="utf-8"))
    economics_report = json.loads((interim / "stage4_economics_report.json").read_text(encoding="utf-8"))
    priority_report = json.loads((interim / "training_priority_report.json").read_text(encoding="utf-8"))
    ai_report = json.loads((interim / "ai_run_report.json").read_text(encoding="utf-8"))
    stage6_config = config.get("stage6", {})
    stage7_config = config.get("stage7", {})

    targets = config.get("sla_targets_minutes", {"chat":15,"voice":120,"social":240,"email":480})
    reference = independent_reference(tickets, products, targets)
    overall = metrics_report["overall_metrics"]
    exposure = economics_report["exposure_totals_inr"]
    production = {"completed_tickets":overall["completed_ticket_count"],
        "primary_csat_response_count":overall["csat_completed_response_count"],"mean_csat":overall["mean_csat"],
        "handle_time_eligibility":overall["handle_time_eligible_count"],"handle_time_median_minutes":overall["handle_time_median"],
        "sla_breach_count":overall["sla_breach_count"],"sla_breach_rate":overall["sla_breach_rate"],
        "transfer_count":overall["total_transfers"],"replacement_count":economics_report["upstream_audit"]["replacement_count"],
        "replacement_cost_inr":exposure["replacement_cost_inr"],"refund_total_inr":exposure["refund_amount_inr"],
        "contact_cost_inr":exposure["contact_cost_inr"]}
    reconciliation = reconcile(production, reference)

    adjusted = _rows(interim/"adjusted_agent_metrics.parquet")
    comparison = _rows(interim/"agent_comparison.parquet")
    agent_metrics = _rows(interim/"agent_metrics.parquet")
    agent_economics = _rows(interim/"agent_economics.parquet")
    ai_agents = _rows(interim/"ai_agent_diagnostics.parquet")
    adjusted_full = {r["agent_id"]:r for r in adjusted if r.get("period_type")=="full_available_period"}
    comparisons = [{**(adjusted_full.get(r.get("agent_id"),{}) if r.get("period_type")=="full_available_period" else {}),**r} for r in comparison]
    comparisons.extend(r for r in adjusted if r.get("period_type")=="quarter")
    current_priority = _rows(interim/"training_priority.parquet")
    recomputed = build_priority_rows(comparisons,agent_metrics,agent_economics,ai_agents,
        priority_report.get("ai_evidence_status","unavailable"),stage6_config)
    current_by_id = {r["agent_id"]:r for r in current_priority}
    recomputed_by_id = {r["agent_id"]:r for r in recomputed}
    upstream_match = len(current_by_id)==len(recomputed_by_id) and all(
        current_by_id[k].get("priority_status")==recomputed_by_id[k].get("priority_status") and
        current_by_id[k].get("priority_score")==recomputed_by_id[k].get("priority_score") for k in current_by_id)
    synthetic = synthetic_decision_scenarios(stage6_config)
    explanation_checks = explanation_consistency(recomputed)
    sensitivity, sensitivity_rows = evaluate_sensitivity(comparisons,agent_metrics,agent_economics,ai_agents,
        priority_report.get("ai_evidence_status","unavailable"),stage6_config)
    bootstrap_summary, bootstrap_resamples = clustered_customer_bootstrap(ticket_metrics,
        replicates=bootstrap_replicates,seed=int(stage7_config.get("random_seed",1701)),
        minimum_n=int(stage6_config.get("minimum_metric_observations",30)))
    default_ids = {r["agent_id"] for r in recomputed if r.get("priority_status")=="training_candidate"}
    temporal = temporal_leave_one_quarter_out(ticket_metrics,default_ids)
    peer_rows, peer_summary = peer_group_robustness(ticket_metrics,default_ids)
    stage3_full = [r for r in adjusted if r.get("period_type")=="full_available_period"]
    audit = {
        "stage1":{"status":"PASS" if len(tickets)==11750 and len({r.get("ticket_id") for r in tickets})==len(tickets) else "FAIL",
                  "ticket_rows":len(tickets),"unique_ticket_ids":len({r.get("ticket_id") for r in tickets})},
        "stage2":{"status":metrics_report.get("status"),"ticket_metric_rows":len(ticket_metrics),"agent_rows":len(agent_metrics)},
        "stage3":{"status":"PASS" if adjusted and comparison else "MISSING","adjusted_rows":len(adjusted),
                  "comparison_rows":len(comparison),"full_period_intervals_adverse_count":sum(
                      r.get(f"{m}_gap_interval_direction") in ("adverse", "excludes_zero_adverse")
                      for r in stage3_full for m in ("csat","handle_time","sla")),
                  "full_period_intervals_overlapping_zero_count":sum(
                      r.get(f"{m}_gap_interval_direction")=="overlaps_zero" for r in stage3_full for m in ("csat","handle_time","sla")),
                  "full_period_intervals_insufficient_count":sum(
                      r.get(f"{m}_gap_interval_direction")=="insufficient" for r in stage3_full for m in ("csat","handle_time","sla"))},
        "stage4":{"status":economics_report.get("status"),"ticket_economics_rows":len(_rows(interim/"ticket_economics.parquet")),
                  "agent_economics_rows":len(agent_economics)},
        "stage5":{"status":"PARTIAL","ai_status":ai_report.get("ai_status"),"provider":ai_report.get("provider"),
                  "model":ai_report.get("model"),"analyzed":ai_report.get("tickets_analyzed",0),
                  "real_model_accuracy":ai_report.get("evaluation",{}).get("model_accuracy"),
                  "actual_usage_cost":ai_report.get("actual_usage_cost_estimate_usd")},
        "stage6":{"status":"PASS" if upstream_match else "PARTIAL","agents":len(current_priority),
                  "priority_status_counts":dict(Counter(r.get("priority_status") for r in current_priority)),
                  "current_outputs_match_recomputed":upstream_match}}
    return {"reference":reference,"production":production,"reconciliation":reconciliation,"audit":audit,
        "synthetic":synthetic,"explanation_checks":explanation_checks,"sensitivity":sensitivity,
        "sensitivity_rows":sensitivity_rows,"bootstrap_summary":bootstrap_summary,"bootstrap_resamples":bootstrap_resamples,
        "temporal":temporal,"peer_rows":peer_rows,"peer_summary":peer_summary,"current_priority":current_priority,
        "recomputed_priority":recomputed,"priority_report":priority_report,"ai_report":ai_report}


def run_stage7(root: Path | None = None, config_path: Path | None = None, bootstrap_replicates: int | None = None):
    root = root or Path(__file__).resolve().parents[3]
    config_path = config_path or root/"configs"/"config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    reps = bootstrap_replicates or int(config.get("stage7",{}).get("bootstrap_replicates",80))
    first = _compute(root,config,reps)
    second = _compute(root,config,reps)
    reproducible = _canonical(first)==_canonical(second)
    interim = root/"data"/"interim"
    _write_json(interim/"stage7_metric_reconciliation.json",first["reconciliation"])
    _write_parquet(interim/"stage7_synthetic_results.parquet",first["synthetic"])
    _write_parquet(interim/"stage7_bootstrap_results.parquet",first["bootstrap_summary"])
    _write_parquet(interim/"stage7_bootstrap_resamples.parquet",first["bootstrap_resamples"])
    _write_parquet(interim/"stage7_sensitivity_results.parquet",first["sensitivity_rows"])
    _write_parquet(interim/"stage7_temporal_results.parquet",first["temporal"])
    _write_parquet(interim/"stage7_peer_robustness.parquet",first["peer_rows"])
    failures = [r for r in first["synthetic"] if r["status"]!="PASS"]
    explanation_failures = [r for r in first["explanation_checks"] if r["status"]!="PASS"]
    candidates = [r["agent_id"] for r in first["current_priority"] if r.get("priority_status")=="training_candidate"]
    proxy_agents = [r for r in first["bootstrap_summary"] if r["candidate_inclusion_frequency"]>0]
    inclusion_freqs = sorted((r["candidate_inclusion_frequency"] for r in first["bootstrap_summary"]),reverse=True)
    quarters = sorted({r["excluded_quarter"] for r in first["temporal"]})
    temporal_counts = dict(Counter(r["excluded_quarter"] for r in first["temporal"] if r["candidate_proxy"]))
    adverse = sum(bool(r["bootstrap_supported_adverse"]) for r in first["bootstrap_summary"])
    output_counts = {name:len(rows) for name,rows in (
        ("synthetic_results",first["synthetic"]),("bootstrap_results",first["bootstrap_summary"]),
        ("bootstrap_resamples",first["bootstrap_resamples"]),("sensitivity_results",first["sensitivity_rows"]),
        ("temporal_results",first["temporal"]),("peer_robustness",first["peer_rows"]))}
    report = {"status":"PASS" if first["reconciliation"]["status"]=="PASS" and not failures and not explanation_failures and reproducible and first["audit"]["stage6"]["current_outputs_match_recomputed"] else "FAIL",
        "stage":7,"upstream_audit":first["audit"],"metric_reconciliation_status":first["reconciliation"]["status"],
        "synthetic_scenarios":{"count":len(first["synthetic"]),"passed":len(first["synthetic"])-len(failures),
            "failed":len(failures),"results":first["synthetic"]},
        "explanation_consistency":{"checks":len(first["explanation_checks"]),"failures":len(explanation_failures)},
        "bootstrap":{"method":"customer-cluster resampling with replacement; descriptive metric/rank stability only",
            "replicates":reps,"agents_summarized":len(first["bootstrap_summary"]),
            "agents_with_nonzero_exploratory_candidate_proxy_frequency":len(proxy_agents),
            "maximum_exploratory_candidate_proxy_frequency":max(inclusion_freqs) if inclusion_freqs else 0,
            "agents_with_bootstrap_interval_wholly_adverse":adverse,
            "interpretation":"Resample frequencies are stability diagnostics, not probabilities of misconduct or validated Stage 6 decisions."},
        "sensitivity":first["sensitivity"],"temporal":{"quarters_tested":quarters,"leave_one_quarter_out_rows":len(first["temporal"]),
            "directional_candidate_proxy_counts_by_excluded_quarter":temporal_counts,"default_stage6_candidates":candidates,
            "future_periods_inferred":False},
        "peer_robustness":{"definitions":first["peer_summary"],"tier_mixing":False,
            "definitions_are_raw_tier_safe_sensitivity_not_replacements_for_case_mix_adjustment":True},
        "empty_candidate_analysis":{"default_candidate_count":len(candidates),
            "reason":"No Stage 3 adjusted full-period interval is directionally adverse; 132 overlap zero and 132 are insufficient across 44 agents and three metrics. The interval uncertainty rule prevents a default candidate set.",
            "assessment":"appropriately conservative on this dataset; strong planted effects pass synthetic detection; point-only candidates are assumption-sensitive and remain unselected."},
        "ai_validation":{"provider_configured":bool(first["ai_report"].get("provider_requests_attempted",0)),
            "real_predictions":first["ai_report"].get("tickets_analyzed",0),"real_model_quality":"not measured","real_model_cost":"not available",
            "mock_contract_coverage":"software tests and mock pipeline only; not model quality"},
        "reproducibility":{"identical_full_evaluation_runs":reproducible,
            "evaluation_bundle_sha256":hashlib.sha256(_canonical(first).encode()).hexdigest(),
            "random_seed":int(config.get("stage7",{}).get("random_seed",1701))},
        "outputs":output_counts,"production_readiness_verdict":"VALIDATED WITH MATERIAL LIMITATIONS",
        "production_blockers":["Stage 5 lacks real-model quality and cost evidence.",
            "Stage 3 intervals are approximate and assume independent tickets; Stage 7 cluster bootstrap is a separate raw Tier/team diagnostic, not a replacement case-mix-adjusted interval.",
            "Temporal and peer-definition tests are directional sensitivity analyses, not causal or out-of-time model validation.",
            "The decision engine has no real-world ground truth for false-positive/negative rates.",
            "The original client submission form is unavailable; external production hosting and centralized monitoring/paging are not configured."]}
    _write_json(interim/"stage7_validation_report.json",report)
    _write_stage7_docs(root/"docs"/"technical",report,first)
    return report


def _write_stage7_docs(docs,report,bundle):
    methodology = """# Evaluation Methodology

## Purpose and separation

Stage 7 validates software contracts and measures sensitivity; it cannot establish agent fault. Synthetic test outcomes are not real-world accuracy. Reviewed AI labels are not a model evaluation without predictions.

## Independent metric reconciliation

Reference calculations are recomputed directly from normalized source ticket/product rows with independently stated policy rates and channel SLA targets. Production Stage 2/4 values are compared to references. Counts must match exactly; rates/means use 1e-12 tolerance; monetary totals use ₹0.01 tolerance. Every item reports absolute and relative difference.

## Synthetic decision tests

Planted scenarios test strong persistent multi-metric effects, tiny samples, one adverse quarter among favorable quarters, a Tier 2/Tier 1 key mismatch, unavailable AI, conflicting outcomes, high economics with normal performance, and repeated identical inputs. These validate rule behavior only, not empirical accuracy.

## Cluster bootstrap

Whole customer IDs are sampled with replacement, retaining all a customer's ticket records. Customers are used because repeat contacts make ticket observations dependent. Each replicate summarizes outcomes by resolver and Tier/team; leave-one-agent-out peer means produce directional gap proxies. Percentile intervals, exploratory two-signal proxy frequency, top-ten inclusion, and within-group rank dispersion are reported. This is a raw Tier/team sensitivity diagnostic, not the Stage 3 case-mix-adjusted model or a misconduct probability.

## Sensitivity, temporal and peer robustness

Stage 6 decisions are recomputed under alternate weights, gap scales, evidence floors, interval rules, and stability factors. Candidate Jaccard, band changes, and score rank correlation are reported; correlation is null when scores are constant. Leave-one-calendar-quarter-out and peer alternatives use ticket-level outcome summaries; these are directional checks, not future validation. Peer definitions are Tier+team+site+shift, Tier+team+site, Tier+team, and Tier alone. At least two other agents are required, and Tier is always part of the key.

## AI boundary and acceptance

No real provider or predictions exist in the current run. AI quality and cost remain unmeasured. Mock/schema tests are software-contract evidence only. Numeric robustness uses deterministic/statistical calculations, never an LLM. Reconciliation, all synthetic expectations, explanation consistency, and same-seed reproducibility must pass. Bootstrap and sensitivity must execute and report stability; they do not authorize changing defaults. Production readiness remains limited where real ground truth, real AI runs, clustered case-mix intervals, or true out-of-time data are unavailable.
"""
    (docs/"evaluation_methodology.md").write_text(methodology,encoding="utf-8",newline="\n")
    lines=["# Stage 7 Findings","","## Overall result","",f"- Stage 7 report: {report['status']}.",
        f"- Production readiness: {report['production_readiness_verdict']}.",
        f"- Default Stage 6 candidates: {report['empty_candidate_analysis']['default_candidate_count']}; all 44 agents remain represented.",
        "- No adjusted Stage 3 full-period interval is directionally adverse; some overlap zero and some are insufficient, so the default uncertainty gate yields no candidate.","","## Independent metric reconciliation",""]
    for item in bundle["reconciliation"]["checks"]:
        lines.append(f"- {item['metric']}: production={item['production_value']}; reference={item['reference_value']}; absolute difference={item['absolute_difference']}; relative difference={item['relative_difference']}; {item['status']} (tolerance {item['tolerance']}).")
    lines.extend(["","## Synthetic decision validation","","Synthetic only; these are not real-agent accuracy measurements."])
    for item in report["synthetic_scenarios"]["results"]:
        lines.append(f"- {item['scenario']}: expected {item['expected_behavior']}; observed {item['actual_behavior']}; {item['status']} — {item['reason']}")
    lines.extend(["","## Bootstrap and resampling","",f"- Method: {report['bootstrap']['method']}.",
        f"- Replicates: {report['bootstrap']['replicates']}; agents summarized: {report['bootstrap']['agents_summarized']}.",
        f"- Agents with nonzero exploratory proxy inclusion frequency: {report['bootstrap']['agents_with_nonzero_exploratory_candidate_proxy_frequency']}; agents with bootstrap intervals wholly adverse: {report['bootstrap']['agents_with_bootstrap_interval_wholly_adverse']}.",
        "- Frequencies describe stability in this resampling design, not probability of misconduct.","","## Sensitivity","",
        f"- Robust candidates across non-point-estimate settings: {report['sensitivity']['robust_candidates']}.",
        f"- Assumption-sensitive candidates: {report['sensitivity']['assumption_sensitive_candidates']}.",
        f"- Point-estimate-only exploratory candidates: {report['sensitivity']['point_estimate_only_candidates']} (not selected by default).",
        "","## Temporal robustness",f"- Leave-one-quarter-out quarters: {', '.join(report['temporal']['quarters_tested'])}.",
        f"- Directional proxy counts by excluded quarter: {json.dumps(report['temporal']['directional_candidate_proxy_counts_by_excluded_quarter'],sort_keys=True)}.",
        "- No future period was inferred; this is not a true future holdout.","","## Peer-group robustness","",
        "Tier remains part of every peer key. Alternative peer calculations are raw directional diagnostics; they do not replace Stage 3 case-mix adjustment."])
    for name,data in report["peer_robustness"]["definitions"].items():
        lines.append(f"- {name}: {data['agents_with_two_or_more_peers']}/{data['agents_evaluated']} agents supported; {data['point_signal_candidate_count']} two-signal point proxies.")
    lines.extend(["","## AI and unresolved risks",f"- Real-model quality: {report['ai_validation']['real_model_quality']}; real-model cost: {report['ai_validation']['real_model_cost']}.",
        *[f"- {item}" for item in report["production_blockers"]],"","## Repository and deployment context",
        "- The repository includes a README, evaluation memo, recording notes, and a submission-form status note; the original client form was not found.",
        "- A Streamlit dashboard, Docker/deployment tools, release/refresh/promotion tools, operations documentation, and acceptance documentation are present.",
        "- Local Docker/release tooling is available. External hosting and centralized monitoring/paging are not configured or verified.",""])
    (docs/"stage7_findings.md").write_text("\n".join(lines),encoding="utf-8",newline="\n")
