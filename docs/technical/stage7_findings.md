# Stage 7 Findings

## Overall result

- Stage 7 report: PASS.
- Production readiness: VALIDATED WITH MATERIAL LIMITATIONS.
- Default Stage 6 candidates: 0; all 44 agents remain represented.
- No adjusted Stage 3 full-period interval is directionally adverse; some overlap zero and some are insufficient, so the default uncertainty gate yields no candidate.

## Independent metric reconciliation

- completed_tickets: production=11183; reference=11183; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.0).
- primary_csat_response_count: production=4947; reference=4947; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.0).
- mean_csat: production=3.325854052961391; reference=3.325854052961391; absolute difference=0.0; relative difference=0.0; PASS (tolerance 1e-12).
- handle_time_eligibility: production=11183; reference=11183; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.0).
- handle_time_median_minutes: production=29.0; reference=29.0; absolute difference=0.0; relative difference=0.0; PASS (tolerance 1e-09).
- sla_breach_count: production=1064; reference=1064; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.0).
- sla_breach_rate: production=0.09055319148936171; reference=0.09055319148936171; absolute difference=0.0; relative difference=0.0; PASS (tolerance 1e-12).
- transfer_count: production=1215; reference=1215; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.0).
- replacement_count: production=1896; reference=1896; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.0).
- replacement_cost_inr: production=3415990.0; reference=3415990.0; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.01).
- refund_total_inr: production=5350871.0; reference=5350871.0; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.01).
- contact_cost_inr: production=3253060.0; reference=3253060.0; absolute difference=0.0; relative difference=0.0; PASS (tolerance 0.01).

## Synthetic decision validation

Synthetic only; these are not real-agent accuracy measurements.
- strong_persistent_effect: expected training_candidate; observed training_candidate:high; PASS — Planted adverse CSAT, handle-time and SLA intervals with ample evidence and two persistent adverse quarters.
- tiny_sample_extreme_gap: expected not_rankable:insufficient_evidence; observed not_rankable:data_quality_restricted,insufficient_evidence; PASS — Extreme point gaps do not bypass the minimum-observation gate.
- one_period_signal: expected not high priority; observed medium; PASS — A single adverse quarter plus otherwise favorable periods cannot receive the persistent high band.
- tier_mismatch: expected blocked by invalid_tier_peer; observed not_rankable:invalid_tier_peer; PASS — The stored peer-group key says Tier 1 while the agent context says Tier 2.
- ai_unavailable: expected same numeric result; AI unavailable; observed unavailable; PASS — No AI diagnostics are present; deterministic scores remain unchanged.
- conflicting_outcomes: expected mixed-performance state; observed mixed_performance; PASS — Adverse CSAT/SLA and favorable handle time remain visible together.
- high_cost_normal_quality: expected no automatic priority from exposure; observed monitor; PASS — Economic exposure is context only and is excluded from the score.
- harmless_perturbation_reproducibility: expected identical deterministic decisions; observed identical; PASS — Repeated evaluation with identical inputs/configuration returns identical records.

## Bootstrap and resampling

- Method: customer-cluster resampling with replacement; descriptive metric/rank stability only.
- Replicates: 80; agents summarized: 44.
- Agents with nonzero exploratory proxy inclusion frequency: 42; agents with bootstrap intervals wholly adverse: 7.
- Frequencies describe stability in this resampling design, not probability of misconduct.

## Sensitivity

- Robust candidates across non-point-estimate settings: [].
- Assumption-sensitive candidates: [].
- Point-estimate-only exploratory candidates: ['A3015', 'A3021', 'A3026'] (not selected by default).

## Temporal robustness
- Leave-one-quarter-out quarters: 2025-Q1, 2025-Q2, 2025-Q3, 2025-Q4, 2026-Q1, 2026-Q2.
- Directional proxy counts by excluded quarter: {"2025-Q1": 20, "2025-Q2": 18, "2025-Q3": 20, "2025-Q4": 21, "2026-Q1": 22, "2026-Q2": 18}.
- No future period was inferred; this is not a true future holdout.

## Peer-group robustness

Tier remains part of every peer key. Alternative peer calculations are raw directional diagnostics; they do not replace Stage 3 case-mix adjustment.
- tier_team_site_shift: 25/44 agents supported; 14 two-signal point proxies.
- tier_team_site: 39/44 agents supported; 16 two-signal point proxies.
- tier_team: 44/44 agents supported; 17 two-signal point proxies.
- tier: 44/44 agents supported; 14 two-signal point proxies.

## AI and unresolved risks
- Real-model quality: not measured; real-model cost: not available.
- Stage 5 lacks real-model quality and cost evidence.
- Stage 3 intervals are approximate and assume independent tickets; Stage 7 cluster bootstrap is a separate raw Tier/team diagnostic, not a replacement case-mix-adjusted interval.
- Temporal and peer-definition tests are directional sensitivity analyses, not causal or out-of-time model validation.
- The decision engine has no real-world ground truth for false-positive/negative rates.
- The original client submission form is unavailable; external production hosting and centralized monitoring/paging are not configured.

## Repository and deployment context
- The repository includes a README, evaluation memo, recording notes, and a submission-form status note; the original client form was not found.
- A Streamlit dashboard, Docker/deployment tools, release/refresh/promotion tools, operations documentation, and acceptance documentation are present.
- Local Docker/release tooling is available. External hosting and centralized monitoring/paging are not configured or verified.
