# Stage 6 Decision Engine

## Objective and boundary

Stage 6 turns Stage 2 performance measures and Stage 3 tier-safe peer comparisons into review priority. It does not make a causal personnel finding. The decision engine is deterministic and does not call an LLM. Stage 5 diagnostics may add themes and representative ticket IDs to explanations, but do not affect eligibility, score, or rank.

## Inputs and joins

The engine reads Stage 2 `agent_metrics` and `agent_assignment_metrics`, Stage 3 `adjusted_agent_metrics` and `agent_comparison`, Stage 4 `agent_economics`, and Stage 5 `ai_agent_diagnostics` plus the AI run report. Agents join by `agent_id`; AI evidence is accepted only when each representative ticket ID also occurs in the successful Stage 5 ticket output and canonical Stage 1 tickets. Quarterly adjusted rows are used for persistence; the full-period comparison supplies the decision outcome and assignment context.

## Eligibility and evidence

Configurable default gates are: at least 30 assignment-context tickets, at least 30 eligible observations for each of CSAT/handle-time/SLA, at least 70% adjustment coverage per measure, at least 70% assignment-context coverage of the agent's total ticket count, a supported peer group, and at least three peer agents. Stage 3 `variable_across_quarters` marks a candidate unstable and not rankable. Failed gates are retained as explicit states (`no_comparable_peer`, `insufficient_evidence`, `data_quality_restricted`, `unstable`); they are not silently dropped. Missing AI evidence is a descriptive status and never an eligibility failure.

Evidence strength is `HIGH` when all three eligible counts are at least 60 and the peer group has at least five agents; `MEDIUM` when all counts meet the 30-observation floor, all adjustment coverage is at least 70%, and peer count is at least three; otherwise it is `LOW`. These are operational evidence labels, not formal statistical power guarantees.

## Signals and uncertainty

Only Stage 3 adjusted gaps are used. Their direction is made consistent: lower CSAT, higher handle time relative to its peer mean, and higher SLA breach rate are adverse. The default concern gate requires the approximate Stage 3 interval to lie wholly in the adverse direction (CSAT upper bound below zero; handle-time/SLA lower bound above zero). A point estimate whose interval overlaps zero is not a confirmed concern.

For a concern that passes the gate, capped severity is scaled by a 0.5-point CSAT gap, a 25% relative handle-time gap, and a 5-percentage-point SLA gap. Configured weights are 0.40, 0.35, and 0.25. The weighted severity is multiplied by evidence factors (HIGH 1.0, MEDIUM 0.75, LOW 0.4) and a stability factor. A training-candidate band requires a confirmed adverse signal and score at least 25; high requires score at least 55 and persistent quarterly adverse intervals. Otherwise an eligible agent is `monitor`. Scores are decision aids under these declared assumptions, not probabilities of agent fault.

Quarterly stability counts intervals wholly adverse/favorable per metric. At least two adverse quarters for one metric is `persistent`; mixed adverse and favorable quarters is `mixed`; one adverse quarter is `single_period`; fewer than two usable quarters is `insufficient_history`; otherwise no adverse quarter signal is recorded. Stage 3 stability labels are retained. Its intervals assume independent tickets and may understate uncertainty due to repeated agents/peer cells.

## Ranking and tier safety

Training priority ranks are assigned only to `training_candidate` rows and only within the same Tier and comparison group. `monitor` and not-rankable rows have no training priority rank. Separately, the dashboard provides Bottom 10 and Top 5 management-review queues. Their review score is the weighted mean of peer-adjusted CSAT gap / 0.5, negative relative handle-time gap / 0.25, and negative SLA gap / 0.05, with each component capped to [-1, 1] and weights 0.40 / 0.35 / 0.25. The score is expressed from -100 (adverse point estimates) to +100 (favorable point estimates); unavailable metrics are omitted and available weights renormalized. Each baseline remains the agent's supported Tier-safe peer comparison; raw metric levels and ticket volume do not determine rank. Score ties break by `agent_id`. The queues surface existing evidence strength, uncertainty, and Stage 6 status and are never retraining or bonus decisions. Tier 1 and Tier 2 are not pooled into peer baselines.

## Economics, budget, and AI

Stage 4 exposures are included only as population-level context (operational, transfer, replacement, refund, and total relevant exposure). They are not included in the priority score because they are not controllable-cost estimates or causal attribution. When the evidence gate yields zero candidates, the dashboard recommends ₹0 for agent-specific retraining and reserves the ₹4,00,000 budget pending stronger evidence or targeted process investigation. Training-cost data is unavailable; the reserve is not savings and no ROI is calculated.

The Overview also states a proposed operational goal to reduce the resolver-associated first-response SLA breach rate by 1 absolute percentage point from the supplied-data baseline. Its policy-credit sensitivity uses the same observed eligible-ticket count and ₹350 per breach. It is not a forecast, causal estimate, or guaranteed credit reduction.

AI status is one of `available`, `partial`, `unavailable`, or `failed`. Themes and cited tickets can appear in a candidate explanation only when a validated Stage 5 row is available. AI confidence never substitutes for sample evidence or uncertainty. The current run has no configured real provider, so AI is unavailable and all numeric decisions use deterministic data only.

## Sensitivity and fallback

The report compares default settings with point-estimate-only exploratory selection, lower/stricter evidence floors, and two alternate metric weight sets. Point-estimate-only candidates are not promoted to the default decision set. AI availability is score-invariant by construction and covered by unit tests. Economic exposure is likewise excluded from score. A candidate set stable across configured scenarios is not proof of validity; Stage 7 must test calibration, error rates, decision stability, edge cases, and reviewer agreement.

Missing AI inputs do not block Stage 6. Missing required deterministic artifacts or duplicate/misaligned agent inputs do block it rather than silently substituting values. The output is analytically ready for Stage 7, not production-validated.
