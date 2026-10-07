# Product Recording Notes (3 minutes maximum)

Record the running dashboard from the verified application and current generated outputs. Keep the story in this order; explain the limited AI evaluation with its full denominator. The supplied recording link is in `submission-form.md`.

## Three-minute storyboard

1. **0:00–0:15 — Request and prompt evolution.** State the original request: per-agent CSAT and handle time, bottom ten flagged, Q3 training budget, and Diwali top five. Briefly say the implementation approach changed from raw ranking to Tier-safe peer comparisons and an evidence gate.
2. **0:15–0:35 — Data and constraints.** Show the reporting period and explain `agent_id` joins, completion-only CSAT, IST timestamps, roster context, and degraded/IVR text limits. Point out that no large-volume paid AI calls were made.
3. **0:35–0:55 — Deterministic analysis.** Show CSAT, handle time, and SLA metrics. Explain that AI does not set numerical metrics or Stage 6 decisions.
4. **0:55–1:15 — Evidence gate and Bottom 10.** State the actual result: **0 defensible training candidates; 44 monitored agents**. Show **Bottom 10 — Review Queue**, its peer-adjusted score and uncertainty/evidence labels. Say it is a management review list, not a retraining recommendation.
5. **1:15–1:30 — Top 5 and budget.** Show **Top 5 — Bonus Review** and clarify it does not determine bonuses. Show the Q3 budget: **₹0 allocated to agent-specific retraining; ₹4,00,000 reserved** pending stronger evidence/process investigation.
6. **1:30–1:50 — Business goal and economics.** Show the proposed 1 percentage-point SLA-breach reduction goal, baseline **9.06%**, target **8.06%**, and same-population **₹41,125** policy-credit sensitivity. State that this is not forecast or guaranteed savings. Show observed contact, replacement, and refund exposure separately; do not attribute it to agents.
7. **1:50–2:10 — Product & Orders.** Show the PL2 versus other-SKU replacement and CSAT signal, supported lot comparisons, order channels, and broad agent-product exposure. Describe them as investigation leads; do not claim a manufacturing cause or agent fault.
8. **2:10–2:30 — Validation.** Show Stage 7: 12 independent reconciliations, eight synthetic decision scenarios, 220 explanation checks, and reproducibility passed. Clarify that synthetic tests are not model accuracy or ground-truth personnel evaluation.
9. **2:30–2:50 — AI, changes, and discarded options.** Explain that the bounded Gemini evaluation attempted 20 requests: 3 outputs passed schema validation and matched their labels, 5 failed schema validation, and 12 received HTTP 429. Only 3/20 cases were scored; do not present 3/3 as overall model accuracy. The prompt contract was tightened afterward and has not been reevaluated live. Point-estimate candidates remain sensitivity analysis only.
10. **2:50–3:00 — Decision and limitations.** Conclude that review lists support investigation while the training gate recommends no agent-specific retraining. Stage 7 remains **VALIDATED WITH MATERIAL LIMITATIONS**.

## Do not claim

- That a Bottom-10 entry should be retrained, or that a Top-5 entry deserves a bonus.
- That the ₹41,125 policy-credit sensitivity is an achieved or causal saving.
- That observed contact/replacement/refund exposure is agent-caused.
- That 3/3 schema-valid predictions represent overall accuracy, or that the revised prompt was evaluated live.
- That external hosting, monitoring, browser filter/export persistence, or target-host acceptance was verified.

Preserve these caveats: approximate independent-ticket uncertainty; no ground-truth personnel-quality error measurement; no genuine out-of-time validation; incomplete clustered case-mix uncertainty; 567 tickets without effective roster context; retained valid handle-time outliers; resolver-associated SLA attribution; and text-quality heuristics that under-detect the IVR junk estimated in the supplied email context.
