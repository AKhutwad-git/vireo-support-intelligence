# Stage 5 AI Evaluation

## Reviewed sample and method

`data/evaluation/ai_human_labels.jsonl` contains 20 manually reviewed ticket labels. Reviewers used customer text only where Stage 1 quality was `usable`; for degraded entries, the issue label is based on agent notes and customer text is explicitly excluded. The sample covers 10 of the 11 observed intake categories, all four channels, High/Normal/Low priority, seven routed teams, and usable/degraded text. `Other` remains uncovered. This small, stratified fixture is not a statistically representative test set.

The bounded real evaluation used the `openai_compatible` provider at Google's Gemini OpenAI-compatible endpoint with `gemini-2.5-flash`, prompt `issue_classification_v1` as it existed at run time, and the existing output validator. It sent only the 20 reviewed ticket IDs; operational candidate ranking did not select the evaluation cases. The run occurred on 2026-10-07 and is recorded in `data/interim/ai_real_evaluation.json` and `data/interim/ai_real_evaluation_errors.jsonl`.

## Latest observed run

- Cases prepared: 20; provider requests: 20; cache hits: 0; cache misses: 20.
- Schema-valid predictions: 3; all 3 matched their human labels (3/3 among valid predictions).
- Schema-validation failures: 5; four `evidence_strength` enum violations and one non-string `policy_process_issue`.
- HTTP failures: 12, all HTTP 429 classified as quota/rate-limit. Transport failures: 0. JSON parse failures: 0.
- Only 3 of 20 cases were scored. The 3/3 agreement is a valid-output subset result, **not overall model accuracy**. The other 17 cases produced no valid prediction, so this run does not establish model accuracy or error rate over all 20 cases.
- Usage metadata was present for 8 of 20 requests: 4,581 observed input tokens, 1,483 observed output tokens, and 17,554 provider-reported total tokens. Usage is incomplete because 12 requests had no usage metadata. Actual billed cost, configured pricing, and a complete usage-based cost estimate are unavailable; cost must not be represented as ₹0.

The observed contract failures led to prompt version `issue_classification_v2`, which explicitly constrains `evidence_strength` to the schema's four exact values and requires `policy_process_issue` to be a string using the existing uncertainty sentinels. **Version 2 has not been evaluated with a live provider.** The latest run above used version 1, so it does not measure whether the prompt change improves output validity.

## Failure analysis and limitations

The four evidence-strength failures violated the allowed string enum (`high`, `insufficient`, `low`, `moderate`); the persisted diagnostics show invalid strings and a numeric value. The policy/process failure returned a non-string. The validator rejected these results rather than broadening the accepted schema. Twelve requests received HTTP 429; these are provider quota/rate-limit failures, not classification errors. No transport or JSON parsing failures were recorded.

The evaluation set is small, fixed, and based on a support intake taxonomy that can be re-tagged at closure. Diagnostic themes and training-topic grouping are subjective, and annotation agreement was not measured. Provider limits affected coverage. Model outputs remain advisory and cannot establish why an outcome occurred or whether an agent caused it. This evaluation does not establish production readiness.

The mock evaluation command and unit tests exercise software contracts, cache behavior, schema validation, error handling, and output persistence. Mock/test results are not model predictions or model-quality metrics. The real-provider evaluation runner is explicitly capped at 20 cases and 20 provider requests; no retry is performed.

## Prompt iteration

The evaluation exposed a concrete output-contract failure in version 1. Version 2 tightens the two observed field contracts; no live result or before/after improvement is claimed for version 2. See `prompt_changelog.md` for the exact change and version history.
