# Prompt Changelog

| Version | Change | Reason | Evaluation result | Decision |
|---|---|---|---|---|
| `issue_classification_v1` | Initial compact prompt; uses the 11 observed intake categories plus abstention/other labels, separates customer intent from issue, requires a short verbatim evidence span, uses notes-only behavior for degraded customer text, and prohibits causal agent claims. | Keep labels anchored in the supplied support taxonomy and control unsupported attribution. | No production model was configured; accuracy, macro-F1, invalid-output, and unsupported-claim rates are not measured. The 20 reviewed ticket labels are ready for a future provider evaluation. | Initial version retained as the only version; no measured improvement is claimed. |

## Discarded approaches

- A large invented issue taxonomy was discarded in favor of the categories already present in the data.
- A single open-ended narrative prompt was discarded in favor of controlled fields, abstention labels, short source-grounded evidence, and Python aggregation of agent summaries.
- Per-ticket calls over all 11,750 records were discarded in favor of deterministic candidate selection and a configurable 250-ticket cap.
- Automatically assigning `other` to every unclear ticket was discarded; `unclear` and `insufficient_evidence` are valid outputs.
- Any model-generated numerical metrics, cost calculations, agent rankings, causal statements, or training priority was excluded.

## Versioning rule

Create a new prompt version only after a held-out reviewed evaluation identifies a concrete failure mode. Record the issue, exact prompt change, sample and metric deltas, reviewer agreement for subjective themes, and keep/revert decision. The mock-client contract smoke test is not a prompt-quality evaluation.
