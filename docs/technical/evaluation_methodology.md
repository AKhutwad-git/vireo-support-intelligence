# Evaluation Methodology

## Purpose and separation

Stage 7 validates software contracts and measures sensitivity; it cannot establish agent fault. Synthetic test outcomes are not real-world accuracy. Reviewed AI labels are not a model evaluation without predictions.

## Independent metric reconciliation

Reference calculations are recomputed directly from normalized source ticket/product rows with independently stated policy rates and channel SLA targets. Production Stage 2/4 values are compared to references. Counts must match exactly; rates/means use 1e-12 tolerance; monetary totals use ₹0.01 tolerance. Every item reports absolute and relative difference.

## Synthetic decision tests

Planted scenarios test strong persistent multi-metric effects, tiny samples, one adverse quarter among favorable quarters, a Tier 2/Tier 1 key mismatch, unavailable AI, conflicting outcomes, high economics with normal performance, and repeated identical inputs. These validate rule behavior only, not empirical accuracy.

## Cluster bootstrap

Whole customer IDs are sampled with replacement, retaining all a customer's ticket records. Customers are used because repeat contacts make ticket observations dependent. Each replicate summarizes outcomes by resolver and Tier/team; leave-one-agent-out peer means produce directional gap proxies. Percentile intervals, exploratory two-signal proxy frequency, top-ten inclusion, and within-group rank dispersion are reported. This is a raw Tier/team sensitivity diagnostic, not the Stage 3 case-mix-adjusted model or a misconduct probability.

## Sensitivity, temporal and peer robustness

Stage 6 decisions are recomputed under alternate weights, gap scales, evidence floors, interval rules, and stability factors. Candidate Jaccard, band changes, and score rank correlation are reported; correlation is null when scores are constant. Leave-one-calendar-quarter-out and peer alternatives use ticket-level outcome summaries; these are directional checks, not future validation. Peer definitions are Tier+team+site+shift, Tier+team+site, Tier+team, and Tier alone. At least two other agents are required, and Tier is always part of the key.

## AI boundary and acceptance

No real provider or predictions exist in the current run. AI quality and cost remain unmeasured. Mock/schema tests are software-contract evidence only. Numeric robustness uses deterministic/statistical calculations, never an LLM. Reconciliation, all synthetic expectations, explanation consistency, and same-seed reproducibility must pass. Bootstrap and sensitivity must execute and report stability; they do not authorize changing defaults. Production readiness remains limited where real ground truth, real AI runs, clustered case-mix intervals, or true out-of-time data are unavailable.
