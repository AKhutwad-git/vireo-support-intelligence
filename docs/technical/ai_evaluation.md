# Stage 5 AI Evaluation

## Reviewed sample

`data/evaluation/ai_human_labels.jsonl` contains 20 manually reviewed ticket labels. Reviewers used customer text only where Stage 1 quality was `usable`; for degraded entries, the issue label is based on the agent notes and the customer message is explicitly excluded. The sample covers 10 of the 11 observed intake categories, all four channels, High/Normal/Low priority, seven routed teams, and usable/degraded text. `Other` remains uncovered in this small, stratified diagnostic fixture, which is not a statistically representative test set.

## Results

No production model/provider was configured during this implementation. Therefore classification accuracy, macro-F1, invalid-output rate, missing-evidence rate, and unsupported-claim rate on the model are **not measured** (null), not zero. The pipeline generated 20 evaluation rows marked `not_run_provider_unavailable` or `not_selected`, with reviewed labels retained and no predicted labels fabricated.

The mock evaluation command exercises provider result parsing, schema validation, evidence checks, output persistence, cache keys, and cost plumbing. Mock-client outcomes are explicitly excluded from model-quality metrics. Unit tests cover valid/uncertain/`other`/insufficient outputs, invalid category/confidence, missing fields, mismatched ticket IDs, non-source evidence, direct causal phrasing, and provider failure. Their pass rates are software-contract test results, not NLP accuracy.

## Error analysis

No real model error cases were observed because there was no provider run. Synthetic adversarial cases are stored in `data/evaluation/ai_error_cases.jsonl`: invalid category, omitted field, mismatched/hallucinated ticket ID, unsupported evidence, causal claim, degraded IVR input, and overconfidence with weak evidence. The validator rejects malformed identity/schema/evidence and causal language. Evaluation flags missing evidence and confidence/evidence-strength mismatch when actual responses become available.

## Limitations

The 20-ticket evaluation fixture is small and its labels use the support intake taxonomy, which can be re-tagged at closure. Diagnostic themes and training-topic grouping are subjective. Stage 1 text quality under-detects IVR junk. Some tickets have ambiguous or incomplete evidence; the model must abstain. A future provider evaluation needs reviewer agreement for subjective diagnostics, held-out tickets, calibration analysis, and adjudication of disagreements. Even a well-performing classifier cannot establish why an outcome occurred or whether an agent caused it.

## Prompt iteration

Only `issue_classification_v1` exists. There is no prior measured production prompt, so no before/after improvement is reported. The initial prompt uses observed support categories, explicit abstention labels, a short evidence-span requirement, degraded-text instructions, and a direct prohibition on agent-causality claims. See `prompt_changelog.md` for discarded options and the criteria for any later version.
