# Stage 3 Findings

Generated from Stage 2 ticket metrics. Results are descriptive adjusted comparisons, not causal explanations or training decisions.

## Peer coverage

- Distinct agents: 44; assignment rows: 44; peer groups: 14.
- Comparable full-period roster assignments: 44 of 44; 44 additional agent context rows lack a resolution-time roster assignment and are retained without peer comparisons.
- Peer fallback requires at least 3 distinct agents in a tier-safe cohort; within-work cells require at least 5 observations from two or more other agents.
- Tier 1 and Tier 2 are never pooled. Peer hierarchy uses tier/team/site/shift when supported, falls back to tier/team, then tier only; unsupported tiers remain un-compared.

## Raw and case-mix adjusted comparisons

Gaps are observed minus leave-one-agent-out expected peer performance on the same case mix. Positive CSAT gaps are higher scores; positive handle-time and SLA gaps are longer times or higher breach rates.

| Outcome | Supported assignment comparisons | Positive gaps | Negative gaps | Median absolute adjusted gap |
|---|---:|---:|---:|---:|
| CSAT (1–5 points) | 44 | 28 | 16 | 0.11 |
| Handle time (minutes) | 44 | 24 | 20 | 93.24 |
| SLA breach-rate points | 44 | 23 | 21 | 0.02 |

Approximate gap-interval directions (interval wholly above zero / wholly below zero / overlaps zero):
- CSAT: above=0, below=0, overlaps=44, insufficient=0.
- CSAT peer-work coverage: mean 100.00%, minimum 100.00% across comparable assignments.
- Handle time: above=0, below=0, overlaps=44, insufficient=0.
- Handle time peer-work coverage: mean 100.00%, minimum 100.00% across comparable assignments.
- SLA: above=0, below=0, overlaps=44, insufficient=0.
- SLA peer-work coverage: mean 100.00%, minimum 100.00% across comparable assignments.

## Case mix and stability

- Agent assignment case mixes are published for channel, priority, category, product family, team, tier, site, shift, and period. Each share has its ticket denominator; missing values have an explicit level.
- Largest observed channel share range across rostered assignment groups for `voice` was 0.4% to 100.0%; this is a mix difference, not a causal effect.
- Largest observed priority share range across rostered assignment groups for `High` was 5.9% to 64.3%; this is a mix difference, not a causal effect.
- Stability is assessed across quarterly intervals with 95% intervals; status counts: {"no_clear_shift_detected": 132}.
- Comparable full-period assignments with fewer than 30 eligible observations: {"csat": 0, "handle_time": 0, "sla": 0}. Month/quarter low-evidence row counts: {"csat": 1011, "handle_time": 829, "sla": 829}. The 30-observation label is descriptive, not a decision threshold.

## Data audit and limitations

- Primary CSAT uses 4,947 valid completed-ticket responses. The 249 populated open/pending scores are excluded from primary CSAT and remain flagged.
- Handle-time distribution retains all 11,183 eligible observations, including 3,451 durations over 24 hours; median 29.00 minutes. No clipping or transformation was applied.
- Stage 1 anomalies remain visible: 206 orders before signup, 19 pre-launch matches, 21 degraded-text heuristic flags, zero exact cross-source duplicate candidates, and 567 tickets without resolution-time roster context.
- Category was not an adjustment predictor because the intake category may be retagged by agents at closure. Transfers, handle time, SLA, refunds, replacements, resolution behavior, and notes are outcome/post-routing fields and were not used as case-mix controls.
- SLA is associated with the ticket's resolving agent because `agent_id` identifies the resolver; the first-response actor is unavailable. Treat these as resolver-associated ticket outcomes, not verified first-responder performance.
- The adjustment uses channel, priority, calendar quarter, product family, and tier-safe peer membership. Peer-cell fallbacks broaden in a fixed order when support is sparse.
- Handle-time durations over 24 hours occur in both sources: helpdesk 2,571/7,994 (over 7 days 392); legacy_fd 880/3,189 (over 7 days 82). This is not isolated to legacy records; the available fields cannot distinguish legitimate long-running cases from timestamp/data artifacts, so observations remain unchanged.
- Approximate confidence intervals assume independent tickets and do not capture agent/period clustering, unobserved case complexity, or selection uncertainty. Observational gaps do not establish causation.
- No global rank, bottom-ten list, or training recommendation is produced.
