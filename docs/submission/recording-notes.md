# Product Recording Notes (3 minutes maximum)

Show the running dashboard itself; no slides are needed. Keep the recording concise and state that Stage 5 is unavailable in the current run.

## Suggested run of show

1. **0:00–0:25 — What was built.** Introduce Vireo as a deterministic support analytics and training decision-support dashboard prepared for the Banao evaluation.
2. **0:25–0:55 — What changed.** Explain the progression from the initial request (“CSAT per agent, handle time per agent, bottom ten flagged”) through source validation, peer/case-mix analysis, economics, decision rules, and Stage 7 evaluation. The bottom-ten framing was not retained as an automatic result.
3. **0:55–1:30 — Overview.** Show the January 2025–June 2026 reporting window, latest quarter 2026 Q2, key performance measures, and the honest outcome of zero training candidates and 44 monitor agents.
4. **1:30–2:05 — Agent views.** Demonstrate filters and the raw versus peer-adjusted versus training-priority views. Open one agent detail page and show evidence, uncertainty, stability, structured explanation, and observed exposure.
5. **2:05–2:30 — Trust and AI.** Show the unavailable AI state and methodology caveats: approximate intervals, no causal attribution, missing roster context, and resolver-associated SLA.
6. **2:30–2:50 — Exports and validation.** Show the CSV download controls and mention Stage 7 reconciliation/synthetic checks. Do not claim the synthetic tests are model accuracy or agent ground truth.

## Prompt/version evolution

The work evolved through explicit implementation stages: trusted data foundation (Stage 1), deterministic metrics (Stage 2), peer/case-mix analysis (Stage 3), economics (Stage 4), optional AI diagnostics (Stage 5, partial), evidence-gated decisions (Stage 6), and evaluation/robustness (Stage 7). This Stage 8 adds a presentation layer and submission documentation without moving analytical calculations into the UI.

## What was discarded or not claimed

- A manufactured bottom-ten list was rejected because no agent passed the default uncertainty gate.
- Point-estimate-only names remain exploratory, not recommended.
- AI-generated accuracy, confidence, cost, and diagnostic evidence are not shown because real predictions/evaluation are unavailable.
- Observed financial exposure is not described as agent-caused cost or guaranteed savings.
- No slides, deployment infrastructure, monitoring, or hosting are included.
