"""Optional Stage 5 orchestration; errors are isolated from deterministic Stages 1-4."""
from __future__ import annotations
import json
from pathlib import Path
from collections import Counter
import pyarrow as pa
import pyarrow.parquet as pq

from vireo.ai.aggregation import aggregate_agent_diagnostics, aggregate_peer_diagnostics
from vireo.ai.cache import ResultCache
from vireo.ai.classification import analyze_batch
from vireo.ai.client import OpenAICompatibleClient, ProviderUnavailable
from vireo.ai.cost import estimate_cost, estimate_tokens
from vireo.ai.diagnosis import to_ticket_row
from vireo.ai.evaluation import error_flags, score_classification
from vireo.ai.prompts import load_prompts
from vireo.ai.selection import score_candidates, select_candidates


def _write(path, rows, schema=None):
    pq.write_table(pa.Table.from_pylist(rows, schema=schema) if rows or schema else pa.table({}), path, compression="zstd")


def run_stage5_ai(interim_dir: Path, config: dict, client=None, project_root: Path | None = None) -> dict:
    project_root = project_root or Path(__file__).resolve().parents[3]
    ai = config.get("ai", {})
    inputs = {name: pq.read_table(interim_dir / f"{name}.parquet").to_pylist() for name in
        ("normalized_tickets", "ticket_metrics", "agent_metrics", "adjusted_agent_metrics", "agent_comparison", "ticket_economics", "agent_economics")}
    # Explicit one-to-one ID joins only; deterministic metrics/economics remain source of truth.
    metrics = {r["ticket_id"]: r for r in inputs["ticket_metrics"]}
    economics = {r["ticket_id"]: r for r in inputs["ticket_economics"]}
    if len(metrics) != len(inputs["ticket_metrics"]) or set(metrics) != set(economics):
        raise ValueError("Stage 5 ticket ID joins are not one-to-one")
    comparisons = {}
    for row in inputs["agent_comparison"]:
        if row.get("period_type") == "full_available_period" and row.get("agent_id"):
            comparisons.setdefault(row["agent_id"], row)
    rows = []
    for source in inputs["normalized_tickets"]:
        tid = source.get("ticket_id")
        m, e = metrics[tid], economics[tid]
        adjusted = comparisons.get(m.get("agent_id"), {})
        rows.append({**source, **m, **e,
            "peer_adjusted_csat_gap": adjusted.get("csat_gap"),
            "peer_adjusted_handle_time_gap": adjusted.get("handle_time_gap"),
            "peer_adjusted_sla_gap": adjusted.get("sla_gap")})
    # Fail closed on required audit fields instead of silently creating hidden substitutions.
    required = {"ticket_id", "agent_id", "channel", "priority", "category", "product_sku", "customer_message", "agent_notes",
        "status", "text_quality_flag", "agent_team", "agent_tier", "agent_assignment_flag", "csat_score_numeric",
        "handle_time_minutes", "valid_for_handle_time", "sla_status", "transfers_numeric", "refund_amount_inr",
        "replacement_issued_flag", "comparison_group"}
    absent = required - set(rows[0]) if rows else required
    if absent: raise ValueError("Stage 5 input fields missing: " + ", ".join(sorted(absent)))
    signals = tuple(ai.get("signals", ()))
    candidate_pool = score_candidates(rows, signals)
    selected = select_candidates(rows, mode=ai.get("selection_mode", "top_n"), max_population=int(ai.get("max_population",250)),
        top_n=int(ai.get("top_n",250)), sample_size=int(ai.get("sample_size",100)), random_seed=int(ai.get("random_seed",1701)),
        agent_id=ai.get("agent_id"), peer_group=ai.get("peer_group"), signals=signals)
    prompt_path = project_root / "configs" / "prompts.yaml"
    prompt_catalog = load_prompts(prompt_path)
    prompt_config = prompt_catalog["issue_classification_v1"]
    version, template = prompt_config["version"], prompt_config["text"]
    configured_model = ai.get("model", "unset")
    errors, analyzed, cached_count = {}, {}, 0
    provider = ai.get("provider", "unconfigured")
    client_error = None
    if client is None and ai.get("enabled"):
        try:
            if configured_model == "unset": raise ProviderUnavailable("AI model is not configured")
            client = OpenAICompatibleClient(ai["endpoint"], configured_model, ai.get("api_key_env", "VIREO_AI_API_KEY"), provider)
        except Exception as exc:
            client_error = type(exc).__name__
    if client is not None:
        provider, configured_model = getattr(client, "provider", provider), getattr(client, "model", configured_model)
        cache_path = Path(ai.get("cache_path", "data/interim/ai_cache.jsonl"))
        if not cache_path.is_absolute(): cache_path = project_root / cache_path
        cache = ResultCache(cache_path)
        # Chunk calls to cap request size and bound individual failure domains.
        for start in range(0, len(selected), max(1, int(ai.get("batch_size",10)))):
            part, part_errors, part_cached = analyze_batch(selected[start:start+max(1,int(ai.get("batch_size",10)))],
                client, template, version, configured_model, cache)
            analyzed.update(part); errors.update(part_errors); cached_count += part_cached
    else:
        client_error = client_error or "provider_disabled"
    analysis_rows = []
    for candidate in selected:
        tid = candidate["ticket_id"]
        if tid in analyzed:
            output = analyzed[tid]
            analysis_rows.append(to_ticket_row(candidate, output["result"], configured_model, version, output["status"]))
        else:
            analysis_rows.append({"ticket_id": tid, "agent_id": candidate.get("agent_id"), "team": candidate.get("agent_team"),
                "status": candidate.get("status"), "attendance_flag": bool(candidate.get("attendance_flag")),
                "tier": candidate.get("agent_tier"), "site": candidate.get("agent_site"), "shift": candidate.get("agent_shift"),
                "agent_from_date": candidate.get("agent_from_date"), "agent_to_date": candidate.get("agent_to_date"),
                "agent_assignment_flag": candidate.get("agent_assignment_flag"), "peer_supported": bool(candidate.get("peer_supported")),
                "comparison_group": candidate.get("comparison_group"),
                "model": configured_model, "prompt_version": version, "issue_category": None, "secondary_category": None,
                "customer_intent": None, "diagnostic_theme": None, "customer_problem": None, "resolution_pattern": None,
                "communication_issue": None, "policy_process_issue": None, "possible_failure_theme": None, "evidence": None,
                "confidence": None, "evidence_strength": None, "text_quality_state": candidate.get("text_quality_state"),
                "selection_signals": candidate.get("selection_signals", []),
                "analysis_status": "provider_unavailable" if client_error else "invalid_model_output"})
    agent_rows = aggregate_agent_diagnostics(analysis_rows)
    peer_rows = aggregate_peer_diagnostics(analysis_rows)
    cache_path = Path(ai.get("cache_path", "data/interim/ai_cache.jsonl")); cache_path = cache_path if cache_path.is_absolute() else project_root / cache_path
    # Only selected requests are token-estimated; pricing remains unknown unless configured.
    prepared_prompts = []
    for row in selected:
        prepared_prompts.append(template.format(ticket_id=row["ticket_id"], channel=row.get("channel") or "unknown",
            priority=row.get("priority") or "unknown", category=row.get("category") or "unknown",
            csat=row.get("csat_score_numeric") if row.get("valid_for_csat") else "not_eligible",
            handle_time=row.get("handle_time_minutes") if row.get("valid_for_handle_time") else "not_eligible",
            sla=row.get("sla_status") or "unknown", transfers=row.get("transfers_numeric") or 0,
            refund="yes" if _positive(row.get("refund_amount_inr")) else "no",
            replacement="yes" if row.get("replacement_issued_flag") else "no",
            peer_csat_gap=row.get("peer_adjusted_csat_gap") if row.get("peer_adjusted_csat_gap") is not None else "unavailable",
            peer_handle_time_gap=row.get("peer_adjusted_handle_time_gap") if row.get("peer_adjusted_handle_time_gap") is not None else "unavailable",
            peer_sla_gap=row.get("peer_adjusted_sla_gap") if row.get("peer_adjusted_sla_gap") is not None else "unavailable",
            customer_message=row.get("analysis_customer_text") or "[excluded: degraded or missing]",
            agent_notes=row.get("analysis_agent_notes") or "[missing]"))
    estimated_in = sum(estimate_tokens(p) for p in prepared_prompts)
    estimated_out = len(selected) * int(ai.get("output_token_estimate_per_ticket",180))
    rates = ai.get("pricing", {})
    cost = estimate_cost(estimated_in, estimated_out, rates)
    actual_in = sum(v["actual_input_tokens"] for v in analyzed.values() if v.get("actual_input_tokens") is not None)
    actual_out = sum(v["actual_output_tokens"] for v in analyzed.values() if v.get("actual_output_tokens") is not None)
    actual_cost = estimate_cost(actual_in, actual_out, rates) if actual_in + actual_out else None
    provider_calls = max(0, len(selected)-cached_count) if client is not None else 0
    if client is not None:
        cached_ids={tid for tid,value in analyzed.items() if value.get("status")=="cached"}
        requested_tokens=sum(estimate_tokens(prompt) for row,prompt in zip(selected,prepared_prompts) if row["ticket_id"] not in cached_ids)
        requested_output_tokens=provider_calls*int(ai.get("output_token_estimate_per_ticket",180))
        estimated_run_cost=estimate_cost(requested_tokens,requested_output_tokens,rates)
    else:
        estimated_run_cost=0.0
        requested_tokens=requested_output_tokens=0
    report = {"status": "PASS", "ai_status": "enabled" if analyzed else "not_configured_or_unavailable", "provider": provider,
        "model": configured_model, "prompt_version": version, "selection_mode": ai.get("selection_mode", "top_n"),
        "candidate_pool_size": len(candidate_pool), "tickets_selected": len(selected), "tickets_analyzed": len(analyzed),
        "tickets_served_from_cache": cached_count, "tickets_skipped": len(rows)-len(selected),
        "provider_requests_attempted": provider_calls,
        "tickets_without_eligible_text_or_signal": len(rows)-len(candidate_pool),
        "eligible_candidates_capped_or_sampled": len(candidate_pool)-len(selected),
        "invalid_or_failed_count": len(errors), "failure_categories": dict(Counter(v.split(":")[0] for v in errors.values())),
        "failure_detail_sample": list(errors.items())[:10], "provider_unavailable_reason": client_error,
        "estimated_input_tokens": estimated_in, "estimated_output_tokens": estimated_out,
        "estimated_input_tokens_for_uncached_requests": requested_tokens,
        "estimated_output_tokens_for_uncached_requests": requested_output_tokens,
        "actual_input_tokens": actual_in if actual_in else None, "actual_output_tokens": actual_out if actual_out else None,
        "pricing_source": rates.get("source"), "pricing_configured": cost is not None,
        "estimated_run_cost_usd": estimated_run_cost, "estimated_cost_if_all_selected_were_analyzed_usd": cost,
        "actual_usage_cost_estimate_usd": actual_cost,
        "estimated_cost_per_analyzed_ticket_usd": estimated_run_cost/len(analyzed) if analyzed and estimated_run_cost is not None else None,
        "monthly_projection": _monthly_projection(len(rows),len(candidate_pool),selected,estimated_in,estimated_out,rates,ai),
        "cache_file": str(cache_path), "cache_stores_raw_text": False,
        "upstream_audit": {name: {"row_count":len(data),"fields":sorted(data[0]) if data else []} for name,data in inputs.items()},
        "text_quality_policy": "usable customer messages may be interpreted; degraded messages are excluded and notes-only use remains labeled with text_quality_state.",
        "evaluation": {"human_label_fixture": "data/evaluation/ai_human_labels.jsonl", "human_reviewed_sample_size": _label_count(project_root), "model_accuracy": None, "macro_f1": None,
            "invalid_output_rate": None,
            "note": "Model performance is not measured when no provider is configured; see evaluation report."}}
    _write(interim_dir/"ai_ticket_analysis.parquet", analysis_rows)
    agent_schema=pa.schema([("agent_id",pa.string()),("sample_size",pa.int64()),("teams",pa.list_(pa.string())),("tiers",pa.list_(pa.string())),
        ("model",pa.string()),("prompt_version",pa.string()),("dominant_issue_themes",pa.list_(pa.struct([("theme",pa.string()),("count",pa.int64())]))),
        ("recurring_failure_patterns",pa.list_(pa.struct([("theme",pa.string()),("count",pa.int64())]))),("themes",pa.list_(pa.struct([("theme",pa.string()),("count",pa.int64())]))),
        ("training_topics",pa.list_(pa.string())),("representative_ticket_ids",pa.list_(pa.string())),("evidence_strength",pa.string()),("overall_evidence_strength",pa.string()),("limitations",pa.list_(pa.string()))])
    _write(interim_dir/"ai_agent_diagnostics.parquet", agent_rows, agent_schema)
    peer_schema=pa.schema([("peer_group_id",pa.string()),("sample_size",pa.int64()),("model",pa.string()),("prompt_version",pa.string()),
        ("dominant_issue_themes",pa.list_(pa.struct([("theme",pa.string()),("count",pa.int64())]))),
        ("recurring_patterns",pa.list_(pa.struct([("theme",pa.string()),("count",pa.int64())]))),("training_topics",pa.list_(pa.string())),
        ("representative_ticket_ids",pa.list_(pa.string())),("evidence_strength",pa.string()),("limitations",pa.list_(pa.string()))])
    _write(interim_dir/"ai_peer_diagnostics.parquet",peer_rows,peer_schema)
    evaluation_rows = _evaluation_rows(project_root, rows, selected, analyzed, errors, client_error)
    _write(interim_dir/"ai_evaluation.parquet", evaluation_rows)
    labels = {r["ticket_id"]: r["reviewed_issue_category"] for r in evaluation_rows}
    predictions = {r["ticket_id"]: r["predicted_issue_category"] for r in evaluation_rows if r.get("predicted_issue_category")}
    model_eval = score_classification(labels, predictions) if getattr(client, "provider", None) != "mock" else {"sample_size":len(labels),"evaluated_count":0,"accuracy":None,"macro_f1":None,"note":"mock provider is protocol smoke only"}
    if getattr(client, "provider", None) == "mock":
        model_eval["note"] = "Mock outputs are excluded from model performance metrics."
    evaluated_results = [v["result"] for k,v in analyzed.items() if k in labels]
    evidence_flags = [error_flags(v, [r.get("analysis_customer_text", ""),r.get("analysis_agent_notes", "")])
        for r in selected if r["ticket_id"] in analyzed for v in [analyzed[r["ticket_id"]]["result"]]]
    attempted_count=max(0,len(selected)-cached_count) if client is not None else 0
    invalid_count=sum(v.startswith("invalid_model_output") for v in errors.values())
    causal_attempts=sum("causal attribution" in v for v in errors.values())
    unsupported_evidence_attempts=sum("evidence" in v and v.startswith("invalid_model_output") for v in errors.values())
    model_eval.update({"invalid_output_rate": invalid_count/attempted_count if attempted_count else None,
        "missing_evidence_rate": sum(x["missing_evidence"] for x in evidence_flags)/len(evidence_flags) if evidence_flags else None,
        "unsupported_claim_rate": (causal_attempts+sum(x["unsupported_claim"] for x in evidence_flags))/attempted_count if attempted_count else None,
        "unsupported_evidence_attempt_rate": (unsupported_evidence_attempts+sum(x["unsupported_evidence"] for x in evidence_flags))/attempted_count if attempted_count else None,
        "overstated_confidence_count": sum(x["overstated_confidence"] for x in evidence_flags)})
    report["evaluation"].update(model_eval)
    report["outputs"] = {name: {"path": str(interim_dir/f"{name}.parquet"), "row_count": count} for name,count in
        (("ai_ticket_analysis",len(analysis_rows)),("ai_agent_diagnostics",len(agent_rows)),("ai_peer_diagnostics",len(peer_rows)),("ai_evaluation",len(evaluation_rows)))}
    report["error_analysis"] = _error_analysis(analysis_rows, errors)
    (interim_dir/"ai_run_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
    return report


def _positive(v):
    try:return float(v or 0)>0
    except (ValueError,TypeError):return False


def _monthly_projection(ticket_count, candidate_count, selected, input_tokens, output_tokens, pricing, ai):
    weekly=float(ai.get("monthly_volume_tickets_per_week",650)); weeks=float(ai.get("weeks_per_month",4.333)); month=weekly*weeks
    rate=candidate_count/ticket_count if ticket_count else 0
    targeted=month*rate
    avg_in=input_tokens/len(selected) if selected else 0; avg_out=output_tokens/len(selected) if selected else 0
    targeted_in,targeted_out=int(targeted*avg_in),int(targeted*avg_out)
    full_in,full_out=int(month*avg_in),int(month*avg_out)
    targeted_cost=estimate_cost(targeted_in,targeted_out,pricing)
    full_cost=estimate_cost(full_in,full_out,pricing)
    return {"assumed_tickets_per_week":weekly,"weeks_per_month":weeks,"monthly_tickets":round(month,2),
        "observed_candidate_rate":rate,"targeted_analysis_tickets_per_month_estimate":round(targeted,2),
        "full_analysis_tickets_per_month_hypothetical":round(month,2),
        "targeted_input_tokens_estimate":targeted_in,"targeted_output_tokens_estimate":targeted_out,
        "full_analysis_input_tokens_estimate":full_in,"full_analysis_output_tokens_estimate":full_out,
        "targeted_monthly_cost_usd_estimate":targeted_cost,"full_monthly_cost_usd_hypothetical":full_cost,
        "cost_status":"unavailable_without_configured_model_pricing" if targeted_cost is None else "estimate_not_provider_invoice"}


def _evaluation_rows(root, rows, selected, analyzed, errors, client_error):
    fixture = root/"data"/"evaluation"/"ai_human_labels.jsonl"
    labels=[]
    if fixture.exists():
        for line in fixture.read_text(encoding="utf-8").splitlines():
            try: labels.append(json.loads(line))
            except json.JSONDecodeError: continue
    by_id={r["ticket_id"]:r for r in rows}
    selected_ids={r["ticket_id"] for r in selected}
    out=[]
    for label in labels:
        pred=analyzed.get(label["ticket_id"],{}).get("result")
        out.append({"ticket_id":label["ticket_id"],"reviewed_issue_category":label["issue_category"],
            "predicted_issue_category":pred.get("issue_category") if pred else None,
            "evaluation_status":"scored" if pred else "not_selected" if label["ticket_id"] not in selected_ids else "not_run_provider_unavailable" if client_error else "not_analyzed",
            "analysis_available":label["ticket_id"] in by_id, "reviewer_note":label.get("reviewer_note")})
    return out


def _label_count(root):
    path=root/"data"/"evaluation"/"ai_human_labels.jsonl"
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()) if path.exists() else 0


def _error_analysis(analysis_rows, errors):
    status_counts=Counter(r.get("analysis_status") for r in analysis_rows)
    return {"analysis_status_counts":dict(status_counts),"invalid_schema_or_provider_failures":len(errors),
        "hallucinated_or_unknown_ticket_id_errors":sum("unknown or duplicate ticket ID" in v for v in errors.values()),
        "unsupported_claims_detected":None,"unsupported_claims_note":"Only validated evidence spans and controlled themes are accepted; human review is still required.",
        "degraded_text_cases_selected":sum(r.get("text_quality_state")=="degraded" for r in analysis_rows),
        "representative_error_ticket_ids":sorted(errors)[:10],
        "failure_modes_reviewed_in_tests":["invalid schema", "unknown ticket ID", "unsupported evidence span", "causal language", "degraded IVR text", "overstated confidence"]}
