"""Run one hard-bounded real-provider evaluation on the reviewed label fixture.

This runner deliberately bypasses operational candidate ranking. It sends only
the 20 IDs in data/evaluation/ai_human_labels.jsonl and never retries a request.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyarrow.parquet as pq

from vireo.ai.cache import ResultCache
from vireo.ai.client import OpenAICompatibleClient
from vireo.ai.cost import estimate_cost, estimate_tokens
from vireo.ai.evaluation import score_classification
from vireo.ai.prompts import load_prompts, ticket_prompt
from vireo.ai.schemas import (CUSTOMER_INTENTS, DIAGNOSTIC_THEMES, EVIDENCE_STRENGTHS,
                              ISSUE_CATEGORIES, SchemaValidationError, validate_ticket_result)
from vireo.ai.selection import eligible_text_sources
from vireo.pipeline.run import load_config

MAX_CASES = 20
MAX_PROVIDER_REQUESTS = 20
LABELS_PATH = ROOT / "data/evaluation/ai_human_labels.jsonl"
RESULT_PATH = ROOT / "data/interim/ai_real_evaluation.json"
ERRORS_PATH = ROOT / "data/interim/ai_real_evaluation_errors.jsonl"
CACHE_PATH = ROOT / "data/interim/ai_real_evaluation_cache.jsonl"
PROMPTS_PATH = ROOT / "configs/prompts.yaml"


class PreflightError(RuntimeError):
    """Raised when a real run cannot safely be prepared."""


def _read_labels() -> list[dict]:
    if not LABELS_PATH.is_file():
        raise PreflightError("human label fixture is missing")
    labels = []
    for line_number, line in enumerate(LABELS_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PreflightError(f"invalid label JSON on line {line_number}") from exc
        if not isinstance(item, dict) or not item.get("ticket_id") or not item.get("issue_category"):
            raise PreflightError(f"label line {line_number} lacks ticket_id or issue_category")
        labels.append(item)
    if len(labels) != MAX_CASES:
        raise PreflightError(f"expected exactly {MAX_CASES} reviewed labels; found {len(labels)}")
    ids = [item["ticket_id"] for item in labels]
    if len(set(ids)) != MAX_CASES:
        raise PreflightError("reviewed label fixture contains duplicate ticket IDs")
    return labels


def _read_table(name: str) -> list[dict]:
    path = ROOT / "data/interim" / f"{name}.parquet"
    if not path.is_file():
        raise PreflightError(f"required local dataset is missing: {name}.parquet")
    return pq.read_table(path).to_pylist()


def _unique_index(rows: list[dict], key: str, table_name: str) -> dict:
    result = {}
    for row in rows:
        value = row.get(key)
        if value in result:
            raise PreflightError(f"{table_name} has duplicate {key} values")
        result[value] = row
    return result


def _prepare_cases(labels: list[dict]) -> list[dict]:
    # Match Stage 5's explicit one-to-one joins, then select only fixture IDs.
    tickets = _unique_index(_read_table("normalized_tickets"), "ticket_id", "normalized_tickets")
    metrics = _unique_index(_read_table("ticket_metrics"), "ticket_id", "ticket_metrics")
    economics = _unique_index(_read_table("ticket_economics"), "ticket_id", "ticket_economics")
    comparisons: dict[str, dict] = {}
    for row in _read_table("agent_comparison"):
        if row.get("period_type") == "full_available_period" and row.get("agent_id"):
            comparisons.setdefault(row["agent_id"], row)

    ids = [label["ticket_id"] for label in labels]
    missing = [tid for tid in ids if tid not in tickets or tid not in metrics or tid not in economics]
    if missing:
        raise PreflightError(f"reviewed ticket IDs missing from canonical datasets or joins: {len(missing)}")

    cases = []
    for label in labels:
        tid = label["ticket_id"]
        metric = metrics[tid]
        adjusted = comparisons.get(metric.get("agent_id"), {})
        row = {**tickets[tid], **metric, **economics[tid],
               "peer_adjusted_csat_gap": adjusted.get("csat_gap"),
               "peer_adjusted_handle_time_gap": adjusted.get("handle_time_gap"),
               "peer_adjusted_sla_gap": adjusted.get("sla_gap")}
        quality, customer_text, notes = eligible_text_sources(row)
        if not customer_text and not notes:
            raise PreflightError(f"reviewed ticket lacks usable text and agent notes: {tid}")
        row["text_quality_state"] = quality
        row["analysis_customer_text"] = customer_text
        row["analysis_agent_notes"] = notes
        row["_human_label"] = label["issue_category"]
        cases.append(row)
    if len(cases) != MAX_CASES or [row["ticket_id"] for row in cases] != ids:
        raise PreflightError("prepared case set does not exactly match the reviewed fixture")
    return cases


def _confusion_metrics(labels: dict[str, str], predictions: dict[str, str]) -> dict:
    scored_labels = {tid: labels[tid] for tid in labels if tid in predictions}
    scored_predictions = {tid: predictions[tid] for tid in scored_labels}
    base = score_classification(scored_labels, scored_predictions)
    classes = sorted(set(scored_labels.values()) | set(scored_predictions.values()))
    matrix = {actual: {predicted: 0 for predicted in classes} for actual in classes}
    per_class = {}
    f1_values = []
    precision_values = []
    recall_values = []
    for tid, actual in scored_labels.items():
        matrix[actual][scored_predictions[tid]] += 1
    for category in classes:
        tp = matrix[category][category]
        fp = sum(matrix[actual][category] for actual in classes if actual != category)
        fn = sum(matrix[category][predicted] for predicted in classes if predicted != category)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[category] = {"precision": precision, "recall": recall, "f1": f1,
                               "support": sum(matrix[category].values())}
        precision_values.append(precision)
        recall_values.append(recall)
        f1_values.append(f1)
    n = len(scored_labels)
    correct = sum(scored_labels[tid] == scored_predictions[tid] for tid in scored_labels)
    base.update({"correct_predictions": correct, "incorrect_predictions": n - correct,
                 "error_rate": (n - correct) / n if n else None,
                 "macro_precision": sum(precision_values) / len(precision_values) if n else None,
                 "macro_recall": sum(recall_values) / len(recall_values) if n else None,
                 "macro_f1": sum(f1_values) / len(f1_values) if n else None,
                 "per_class": per_class, "confusion_matrix": matrix})
    return base


def _schema_diagnostic(exc: Exception, value) -> dict:
    """Return useful validation context without persisting model text/evidence."""
    message = str(exc)
    diagnostic = {"failure_stage": "schema_validation",
                  "exception_class": type(exc).__name__,
                  "validation_field": None,
                  "validation_error_type": "schema_constraint",
                  "validation_message": message,
                  "constraint": None}
    if not isinstance(exc, SchemaValidationError):
        diagnostic["validation_error_type"] = "unexpected_validation_error"
        diagnostic["validation_message"] = "Output validation failed; details omitted."
        return diagnostic
    match = re.fullmatch(r"invalid (issue_category|secondary_category|customer_intent|diagnostic_theme|evidence_strength)", message)
    if match:
        field = match.group(1)
        allowed = {"issue_category": ISSUE_CATEGORIES, "secondary_category": ISSUE_CATEGORIES,
                   "customer_intent": CUSTOMER_INTENTS, "diagnostic_theme": DIAGNOSTIC_THEMES,
                   "evidence_strength": EVIDENCE_STRENGTHS}[field]
        received = value.get(field) if isinstance(value, dict) else None
        diagnostic.update({"validation_field": field, "validation_error_type": "enum",
                           "constraint": {"allowed_values": sorted(allowed)},
                           "received_value_type": type(received).__name__,
                           "received_value_length": len(received) if isinstance(received, str) else None})
        return diagnostic
    fields_match = re.fullmatch(r"schema fields mismatch; missing=(\[.*?\]), extra=(\[.*\])", message)
    if fields_match:
        try:
            missing = ast.literal_eval(fields_match.group(1))
            extra = ast.literal_eval(fields_match.group(2))
        except (ValueError, SyntaxError):
            missing, extra = [], []
        diagnostic.update({"validation_field": "object.fields", "validation_error_type": "field_set",
                           "constraint": {"missing_required_fields": missing, "unexpected_fields": extra}})
        return diagnostic
    known = (
        ("model output must be a JSON object", "$", "object_type", "JSON object required"),
        ("model returned a ticket ID outside the request", "ticket_id", "identity", "must equal the requested ticket ID"),
        ("confidence must be numeric and between 0 and 1", "confidence", "type_or_range", "number in [0, 1]"),
        ("must be a string", None, "field_type", "string required"),
        ("exceeds the maximum length", None, "max_length", "maximum 500 characters"),
        ("evidence must be a short exact span from supplied text", "evidence", "evidence_span", "verbatim source span; maximum 280 characters"),
        ("insufficient evidence output must not cite an evidence span", "evidence", "evidence_consistency", "empty evidence when issue_category is insufficient_evidence"),
        ("unsupported causal attribution language", "$text_fields", "causal_claim", "must not assert agent causality"),
    )
    for fragment, field, error_type, constraint in known:
        if fragment in message:
            if field is None:
                field = message.split(" ", 1)[0]
            diagnostic.update({"validation_field": field, "validation_error_type": error_type,
                               "constraint": constraint})
            length_field = field if isinstance(field, str) and field in (value or {}) else None
            if length_field and isinstance(value[length_field], str):
                diagnostic["received_value_length"] = len(value[length_field])
            return diagnostic
    diagnostic.update({"validation_field": "$", "validation_error_type": "schema_constraint",
                       "constraint": "See validation_message; no model text included."})
    return diagnostic


def _classify_http_status(status) -> str:
    if status == 400:
        return "request_rejected"
    if status == 401:
        return "authentication_failure"
    if status == 403:
        return "access_denied"
    if status == 404:
        return "endpoint_or_model_not_found"
    if status == 408:
        return "http_timeout"
    if status == 429:
        return "quota_or_rate_limit"
    if isinstance(status, int) and 500 <= status <= 599:
        return "provider_server_error"
    return "provider_http_error"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    temporary.replace(path)


def run(*, preflight_only: bool = False) -> dict:
    config = load_config(ROOT / "configs/config.yaml")
    ai = config.get("ai", {})
    # This dedicated script is itself an explicit opt-in action for a bounded
    # real-provider evaluation. Enable AI only in this freshly loaded in-memory
    # configuration; the application default in configs/config.yaml stays off.
    ai["enabled"] = True
    provider = ai.get("provider")
    model = ai.get("model")
    endpoint = ai.get("endpoint")
    key_env = ai.get("api_key_env", "VIREO_AI_API_KEY")
    if provider != "openai_compatible" or not endpoint:
        raise PreflightError("configured provider or endpoint is missing/unsupported")
    if not model or model == "unset":
        raise PreflightError("AI model is not configured")
    if not os.environ.get(key_env):
        raise PreflightError(f"provider key is not set in environment variable {key_env}")

    labels = _read_labels()
    cases = _prepare_cases(labels)
    catalog = load_prompts(PROMPTS_PATH)
    prompt_config = catalog["issue_classification_v1"]
    prompt_version, template = prompt_config["version"], prompt_config["text"]
    prompts = {row["ticket_id"]: ticket_prompt(row, template) for row in cases}
    if len(prompts) != MAX_CASES or any(not prompt for prompt in prompts.values()):
        raise PreflightError("exactly 20 non-empty versioned prompts were not prepared")

    # Construction validates provider configuration and credentials; it does not send a request.
    try:
        client = OpenAICompatibleClient(endpoint, model, key_env, provider)
    except Exception as exc:
        raise PreflightError(f"provider client initialization failed: {type(exc).__name__}") from exc
    if client.model != model or client.provider != provider:
        raise PreflightError("initialized client identity differs from configured provider/model")

    cache = ResultCache(CACHE_PATH)
    # A separate cache namespace prevents older mock/operational cache entries from
    # being mistaken for real-evaluation predictions. Repeated real runs reuse these.
    cache_model_key = f"real-evaluation:{provider}:{model}"
    label_by_id = {label["ticket_id"]: label["issue_category"] for label in labels}
    predictions: dict[str, dict] = {}
    cache_hits = 0
    misses: list[dict] = []
    errors: dict[str, dict] = {}
    case_status: dict[str, str] = {}
    usage_by_id: dict[str, dict] = {}
    for row in cases:
        tid = row["ticket_id"]
        sources = [text for text in (row["analysis_customer_text"], row["analysis_agent_notes"]) if text]
        key = cache.make_key(prompts[tid], cache_model_key, prompt_version)
        cached = cache.get(key)
        if cached is not None:
            try:
                validated = validate_ticket_result(cached, tid, sources)
            except Exception:
                # Invalid cache entries are misses, never treated as predictions.
                misses.append({"ticket_id": tid, "prompt": prompts[tid], "_key": key, "_sources": sources})
            else:
                predictions[tid] = {"result": validated, "source": "real_evaluation_cache",
                                    "actual_input_tokens": None, "actual_output_tokens": None}
                cache_hits += 1
                case_status[tid] = "valid_prediction"
        else:
            misses.append({"ticket_id": tid, "prompt": prompts[tid], "_key": key, "_sources": sources})

    if len(cases) > MAX_CASES or len(misses) > MAX_PROVIDER_REQUESTS:
        raise PreflightError("hard evaluation/request cap exceeded")
    preflight = {"provider": provider, "model": model, "prompt_version": prompt_version,
                 "prepared_cases": len(cases), "cache_hits": cache_hits,
                 "cache_misses": len(misses), "maximum_cases": MAX_CASES,
                 "maximum_provider_requests": MAX_PROVIDER_REQUESTS,
                 "provider_client_initialized": True}
    if preflight_only:
        return {**preflight, "status": "PREFLIGHT_PASS_NO_PROVIDER_CALLS"}

    # Exactly one client invocation; the existing HTTP client sends one request per
    # item and performs no retries. The number of items was checked against the cap.
    provider_requests = len(misses)
    if provider_requests:
        if provider_requests > MAX_PROVIDER_REQUESTS:
            raise PreflightError("provider request hard cap exceeded")
        request_items = [{"ticket_id": item["ticket_id"], "prompt": item["prompt"]} for item in misses]
        try:
            returned = client.classify_batch(request_items)
        except Exception as exc:
            # One invocation, no retry. Preserve only the exception class.
            returned = [{"ticket_id": item["ticket_id"], "error": type(exc).__name__,
                         "failure": {"failure_stage": "transport",
                                     "exception_class": type(exc).__name__,
                                     "safe_message": None}} for item in request_items]
        expected = {item["ticket_id"] for item in misses}
        seen = set()
        miss_by_id = {item["ticket_id"]: item for item in misses}
        for response in returned:
            if not isinstance(response, dict):
                continue
            tid = response.get("ticket_id")
            if tid not in expected or tid in seen:
                # The unexpected response is kept as a run-level diagnostic only;
                # it cannot be attributed to a reviewed case safely.
                continue
            seen.add(tid)
            miss = miss_by_id[tid]
            usage = {"input_tokens": response.get("actual_input_tokens"),
                     "output_tokens": response.get("actual_output_tokens"),
                     "total_tokens": response.get("actual_total_tokens")}
            if any(value is not None for value in usage.values()):
                usage_by_id[tid] = usage
            if response.get("error"):
                failure = response.get("failure") or {
                    "failure_stage": "provider_response",
                    "exception_class": str(response.get("error"))[:80],
                    "safe_message": None}
                stage = failure.get("failure_stage", "provider_response")
                classification = (_classify_http_status(failure.get("http_status"))
                                  if stage == "provider_http" else
                                  "network_or_timeout" if stage == "transport" else
                                  "invalid_provider_json" if stage == "json_parse" else
                                  "provider_response_error")
                record = {"ticket_id": tid, "failure_stage": stage,
                          "error_classification": classification,
                          "exception_class": failure.get("exception_class"),
                          "model": model, "prompt_version": prompt_version}
                for field in ("http_status", "provider_error_code", "provider_error_type",
                              "provider_error_message", "safe_response_detail", "safe_message"):
                    if failure.get(field) is not None:
                        record[field] = failure[field]
                errors[tid] = record
                case_status[tid] = {"provider_http": "provider_http_failure",
                                    "transport": "transport_failure",
                                    "json_parse": "json_parse_failure"}.get(stage, "provider_response_failure")
                continue
            try:
                validated = validate_ticket_result(response.get("result"), tid, miss["_sources"])
            except SchemaValidationError as exc:
                record = {"ticket_id": tid,
                          "error_classification": "schema_validation_failure",
                          "model": model, "prompt_version": prompt_version,
                          **_schema_diagnostic(exc, response.get("result"))}
                errors[tid] = record
                case_status[tid] = "schema_validation_failure"
                continue
            except Exception as exc:
                record = {"ticket_id": tid, "failure_stage": "application_validation",
                          "error_classification": "unexpected_validation_error",
                          "exception_class": type(exc).__name__,
                          "validation_field": "$", "validation_error_type": "unexpected",
                          "validation_message": "Output validation failed; details omitted.",
                          "model": model, "prompt_version": prompt_version}
                errors[tid] = record
                case_status[tid] = "other_failure"
                continue
            predictions[tid] = {"result": validated, "source": "provider",
                                "actual_input_tokens": response.get("actual_input_tokens"),
                                "actual_output_tokens": response.get("actual_output_tokens"),
                                "actual_total_tokens": response.get("actual_total_tokens")}
            case_status[tid] = "valid_prediction"
            try:
                cache.set(miss["_key"], validated)
            except OSError:
                # A valid response remains scored if local cache persistence fails.
                pass
        for tid in expected - seen:
            errors[tid] = {"ticket_id": tid, "failure_stage": "provider_response",
                          "error_classification": "provider_omitted_result",
                          "exception_class": None, "model": model,
                          "prompt_version": prompt_version}
            case_status[tid] = "other_failure"

    result_by_id = {}
    disagreement_records = []
    for tid, human_label in label_by_id.items():
        prediction = predictions.get(tid)
        predicted_label = prediction["result"]["issue_category"] if prediction else None
        correct = predicted_label == human_label if predicted_label is not None else None
        result_by_id[tid] = {"ticket_id": tid, "human_label": human_label,
                             "predicted_label": predicted_label, "correct": correct,
                             "status": "scored" if prediction else case_status.get(tid, "other_failure"),
                             "prediction_source": prediction["source"] if prediction else None,
                             "confidence": prediction["result"].get("confidence") if prediction else None}
        if predicted_label is not None and not correct:
            disagreement_records.append({"record_type": "disagreement", "ticket_id": tid,
                                          "human_label": human_label, "predicted_label": predicted_label,
                                          "correct": False, "model": model,
                                          "prompt_version": prompt_version})
        elif not prediction:
            failure = errors.get(tid, {"failure_stage": "provider_response",
                                       "error_classification": "prediction_unavailable"})
            disagreement_records.append({**failure, "record_type": "failed_case",
                                          "human_label": human_label,
                                          "predicted_label": None})

    predicted_labels = {tid: item["result"]["issue_category"] for tid, item in predictions.items()}
    metrics = _confusion_metrics(label_by_id, predicted_labels)
    provider_successes = sum(item["source"] == "provider" for item in predictions.values())
    usage_complete = provider_requests > 0 and all(
        tid in usage_by_id and usage_by_id[tid].get("input_tokens") is not None
        and usage_by_id[tid].get("output_tokens") is not None
        for tid in (item["ticket_id"] for item in misses))
    observed_input = sum(item.get("input_tokens") or 0 for item in usage_by_id.values())
    observed_output = sum(item.get("output_tokens") or 0 for item in usage_by_id.values())
    observed_total_values = [item.get("total_tokens") for item in usage_by_id.values()
                             if item.get("total_tokens") is not None]
    usage_in = sum(usage_by_id[tid]["input_tokens"] for tid in usage_by_id
                   if usage_by_id[tid].get("input_tokens") is not None)
    usage_out = sum(usage_by_id[tid]["output_tokens"] for tid in usage_by_id
                    if usage_by_id[tid].get("output_tokens") is not None)
    rates = ai.get("pricing", {})
    usage_estimate = estimate_cost(usage_in, usage_out, rates) if usage_complete else None
    estimated_input = sum(estimate_tokens(prompts[item["ticket_id"]]) for item in misses)
    estimated_output = len(misses) * int(ai.get("output_token_estimate_per_ticket", 180))
    estimated_cost = estimate_cost(estimated_input, estimated_output, rates)
    status_counts = Counter(case_status.get(tid, "other_failure") for tid in label_by_id)
    http_failures = status_counts["provider_http_failure"]
    transport_failures = status_counts["transport_failure"]
    parse_failures = status_counts["json_parse_failure"]
    schema_failures = status_counts["schema_validation_failure"]
    failure_records = list(errors.values())
    failure_records.extend(record for record in disagreement_records
                           if record.get("record_type") == "disagreement")
    result_by_id_list = list(result_by_id.values())
    for result_row in result_by_id_list:
        failure = errors.get(result_row["ticket_id"])
        if failure:
            result_row["failure_stage"] = failure.get("failure_stage")
            result_row["error_classification"] = failure.get("error_classification")
    report = {**preflight, "status": "COMPLETE", "run_timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "evaluation_cases": MAX_CASES, "cases_evaluated": metrics["evaluated_count"],
              "valid_predictions": len(predictions), "successful_predictions": len(predictions),
              "successful_provider_predictions": provider_successes,
              "failed_provider_requests": http_failures + transport_failures,
              "provider_http_failures": http_failures, "transport_failures": transport_failures,
              "json_parse_failures": parse_failures, "schema_validation_failures": schema_failures,
              "other_failures": status_counts["other_failure"],
              "failure_counts_by_case_status": dict(status_counts),
              "failed_cases": MAX_CASES - len(predictions),
              "provider_requests": provider_requests, "cache_hits": cache_hits, "cache_misses": len(misses),
              "metrics_denominator": metrics["evaluated_count"], "metrics": metrics,
              "token_usage": {"input_tokens": usage_in if usage_complete else None,
                              "output_tokens": usage_out if usage_complete else None,
                              "total_tokens": sum(observed_total_values) if usage_complete and len(observed_total_values) == provider_requests else None,
                              "observed_input_tokens_sum": observed_input if usage_by_id else None,
                              "observed_output_tokens_sum": observed_output if usage_by_id else None,
                              "observed_total_tokens_sum": sum(observed_total_values) if observed_total_values else None,
                              "responses_with_usage": len(usage_by_id),
                              "provider_requests_without_usage": provider_requests - len(usage_by_id)},
              "cost": {"actual_billed_cost": None,
                       "usage_based_estimate_usd": usage_estimate,
                       "request_token_estimate_usd": estimated_cost,
                       "pricing_source": rates.get("source"),
                       "note": "Provider response does not report billed cost; usage estimates require complete usage and configured pricing."},
              "cache_file": str(CACHE_PATH.relative_to(ROOT)),
              "results": result_by_id_list,
              "case_status_counts": {"valid_prediction": status_counts["valid_prediction"],
                                     "provider_http_failure": http_failures,
                                     "transport_failure": transport_failures,
                                     "json_parse_failure": parse_failures,
                                     "schema_validation_failure": schema_failures,
                                     "other_failure": status_counts["other_failure"]},
              "limitations": ["Small, fixed 20-case human-reviewed diagnostic sample.",
                              "Metrics use successful predictions as their denominator.",
                              "Cached predictions are prior outputs from this runner's real-provider namespace.",
                              "This evaluation does not establish causal personnel effects or production readiness."]}
    _write_json(RESULT_PATH, report)
    _write_jsonl(ERRORS_PATH, failure_records)
    print(json.dumps({"status": report["status"], "provider": provider, "model": model,
                      "evaluation_cases": MAX_CASES, "provider_requests": provider_requests,
                      "valid_predictions": len(predictions), "provider_http_failures": http_failures,
                      "transport_failures": transport_failures, "json_parse_failures": parse_failures,
                      "schema_validation_failures": schema_failures,
                      "cache_hits": cache_hits, "cache_misses": len(misses),
                      "results_file": str(RESULT_PATH.relative_to(ROOT)),
                      "errors_file": str(ERRORS_PATH.relative_to(ROOT))}, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true",
                        help="validate credentials/config/data/prompts/cache without making provider requests")
    args = parser.parse_args()
    try:
        report = run(preflight_only=args.preflight_only)
    except (PreflightError, OSError, ValueError) as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr)
        return 2
    if args.preflight_only:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
