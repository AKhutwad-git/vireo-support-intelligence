# Stage 5 AI Diagnostic Architecture

## Responsibilities and boundary

Stage 5 labels issue themes and summarizes ticket evidence for later review. Stage 1–4 remain authoritative for ticket counts, CSAT, handle time, SLA, transfers, costs, refunds, replacement amounts, peer baselines, and opportunities. The model receives selected deterministic values as context only. It cannot write or override those values. No ranking, training score, ROI, or causal attribution is produced.

## Data flow and joins

The Stage 5 orchestrator reads canonical tickets, Stage 2 ticket and agent metrics, Stage 3 adjusted-agent/comparison context, and Stage 4 ticket/agent economics. It validates ticket IDs and joins on `ticket_id`; peer/agent context comes from the already-built deterministic analysis outputs. There are no text-derived hidden joins. A candidate carries documented `agent_id`, team/tier, category, channel, priority, SKU, Stage 1 text-quality flag, roster provenance, Stage 2 outcomes, and Stage 4 refund/replacement/repeat flags.

## Deterministic candidate selection

Current configurable signals are CSAT ≤2, handle time at or above the eligible-ticket 90th percentile, SLA breach, repeat-contact candidate, refund or replacement, and at least two transfers. Selection is rule-based, ordered by number of signals then `ticket_id`, and capped at 250 by default. Modes include all eligible candidates, top-N, seeded sample, agent sample, and peer-group sample. No model chooses candidates. “All” means all tickets with at least one enabled candidate signal and usable text, still subject to the configured maximum.

## Text quality

When Stage 1 marks a customer message usable, the clipped message and notes may be considered. For degraded/missing message text, that message is excluded; the model may receive notes only, and the original text-quality state remains on the result. No-text tickets are ineligible. The heuristic flagged 21 messages, while the source email estimated roughly 40 IVR artifacts; this detector is known to under-detect.

## Provider, prompt, and schema

`vireo.ai.client.AIClient` is the provider-neutral interface. `OpenAICompatibleClient` is the OpenAI-compatible JSON HTTP implementation selected through configuration; credentials are read from the configured environment variable and are not stored in YAML. No conversation text is transmitted when AI is disabled or the provider is unavailable. The prompt catalog retains the `issue_classification_v1` lookup key for runtime compatibility and currently identifies prompt version `issue_classification_v2`. Its taxonomy derives from observed categories plus `Other`, `other`, `unclear`, and `insufficient_evidence`. Typed runtime validation checks exact fields, allowed labels, confidence bounds, ticket identity, causal phrasing, and that the short evidence span occurs exactly in supplied text.

The validated ticket output includes issue, intent, resolution pattern, communication/process signals, possible theme, evidence, confidence, model, prompt version, and text quality. Agent summaries are deterministic Python aggregates over validated, completed-ticket analyses only. They cite only ticket IDs present in that set; at least two matching diagnostic-theme occurrences are needed to emit a recurring pattern/training topic. They remain descriptive, not recommendations.

## Cache, limits, and failure behavior

Cache keys hash full prompt input with model ID and prompt version. JSONL cache entries hold only the key and schema-validated result/evidence span, not the raw prompt or conversation. Provider errors, malformed outputs, omitted results, and unsupported evidence are isolated per batch/ticket and recorded without raw customer text. Missing provider configuration produces `provider_unavailable` rows, zero analyzed tickets, and null performance/cost values. Stage 5 exceptions are reported as `DEGRADED` and do not fail or mutate deterministic Stage 1–4 outputs.

## Human review

Twenty reviewed labels are stored in `data/evaluation/ai_human_labels.jsonl`, with examples across observed issue categories, four channels, three priority levels, seven routed teams, and both usable/degraded text. `data/evaluation/ai_error_cases.jsonl` records synthetic contract-failure cases used by tests; these are not claimed as observed model errors. A separate bounded real evaluation made 20 requests to Gemini 2.5 Flash: 3 outputs passed schema validation and matched their labels, 5 failed validation, and 12 returned HTTP 429. The 3/3 result is only among valid outputs and is not overall model accuracy; the run does not establish model quality or production readiness. See `ai_evaluation.md` for usage/cost limitations and complete denominators.
