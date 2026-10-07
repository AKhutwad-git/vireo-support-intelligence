# Prompt Changelog

The prompt catalog retains the `issue_classification_v1` lookup key for runtime compatibility. Its `version` field is the cache/evaluation version identifier.

| Version | Change | Reason | Evaluation result | Decision |
|---|---|---|---|---|
| `issue_classification_v1` | Initial compact prompt with observed issue categories, abstention values, source-grounded evidence, degraded-text instructions, and a prohibition on agent-causality claims. | Anchor outputs in the supplied taxonomy and limit unsupported attribution. | The bounded real run attempted 20 requests: 3 valid predictions, all 3 matching labels; 5 schema failures; 12 HTTP 429 quota/rate-limit failures; 0 transport/JSON parse failures. Only 3/20 were scored, so 3/3 is not overall model accuracy. | Observed `evidence_strength` enum violations and a non-string `policy_process_issue` prompted a contract clarification. |
| `issue_classification_v2` | Explicitly requires `evidence_strength` to be exactly one of `high`, `insufficient`, `low`, or `moderate`; requires `policy_process_issue` to always be a string and uses `unclear` / `insufficient_evidence` as uncertainty sentinels. | Address the two output-contract failures observed in the version 1 real evaluation without broadening schema acceptance. | Not evaluated with a live provider. The version 1 results above are not evidence of version 2 performance. | Retain for offline contract testing; do not claim improved validity or accuracy until separately evaluated. |

## Other design choices

- A large invented issue taxonomy was discarded in favor of categories already present in the data.
- A single open-ended narrative prompt was discarded in favor of controlled fields, abstention values, short source-grounded evidence, and Python aggregation.
- Per-ticket calls over all 11,750 records were discarded; the dedicated evaluation runner is capped at the fixed 20 reviewed cases and 20 requests.
- Automatically assigning `other` to every unclear ticket was discarded; `unclear` and `insufficient_evidence` are valid outputs where appropriate.
- Model-generated numerical metrics, cost calculations, agent rankings, causal statements, and training priorities remain excluded.
