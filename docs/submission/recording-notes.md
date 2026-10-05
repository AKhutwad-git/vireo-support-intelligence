# Product Recording Notes (3 minutes maximum)

Record the running dashboard from the locally verified image and bundle pair listed in `release-record.md`. No slides are required. Keep the story in this order and do not imply a live AI run.

## Storyboard

1. **0:00–0:15 — Request.** “The request was CSAT per agent, handle time per agent, and a bottom-ten list flagged for action.” Explain that the list was a request to investigate, not a result to manufacture.
2. **0:15–0:35 — Data and policy.** Show the reporting period and explain that ticket grain, completion-only CSAT, effective-dated roster assignments, support policy, and missing roster context were checked before comparisons.
3. **0:35–1:00 — Deterministic analysis.** Summarize the operational measures and show that the calculations are deterministic. Explain that AI does not set the numeric metrics or decision.
4. **1:00–1:20 — Peer comparison.** Show Tier-safe peer/case-mix comparisons. Raw point estimates are descriptive; uncertainty and evidence requirements control whether an agent can be recommended.
5. **1:20–1:40 — Evidence gate.** Show the gate and the actual result: **0 defensible training candidates; 44 agents monitored**. The default gate did not support a bottom-ten recommendation.
6. **1:40–2:00 — Dashboard.** Demonstrate the Overview and Agents pages, including filters and the raw, peer-adjusted, and training-priority views. Open one agent detail to show evidence and uncertainty.
7. **2:00–2:20 — Economics.** Show observed contact, replacement, and refund exposure as separate population context. State that these are not agent-caused costs or guaranteed savings.
8. **2:20–2:40 — Validation.** Show the Stage 7 summary: 12 independent reconciliations, eight synthetic scenarios, 220 explanation checks, and reproducibility passed. Clarify that synthetic checks are not model accuracy or ground-truth personnel evaluation.
9. **2:40–3:00 — Decision and boundary.** Conclude: “The system does not manufacture a bottom-ten ranking when the evidence does not support one.” State that Stage 5 AI was unavailable in this evaluation run, so no live AI predictions or model-quality claims are shown. Stage 7 remains **VALIDATED WITH MATERIAL LIMITATIONS**.

## Presentation notes

- Keep the initial request, validated data, deterministic analysis, evidence gate, dashboard, economics, validation, and final decision in that order.
- Stage 5 is optional; it made zero real provider requests in the current evaluation run. Do not present cached, mock, or synthetic evidence as live model output.
- Preserve these caveats: approximate uncertainty, no ground-truth agent-quality error measurement, no genuine out-of-time validation, incomplete clustered case-mix uncertainty, 567 tickets without effective roster context, retained handle-time outliers, and resolver-associated SLA attribution.
- Point-estimate-only sensitivity names remain exploratory and must not be described as recommended training candidates.
- Local Docker and release tooling exist. External hosting is not configured or verified; centralized monitoring and paging are not configured. No slides are needed.
