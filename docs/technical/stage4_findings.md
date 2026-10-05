# Stage 4 Economics Findings

Descriptive policy-backed cost exposures; scenarios are hypothetical and do not establish savings or causality.

## Observed exposure

- Contact cost exposure: ₹3,253,060.00.
- SLA breach credit exposure: ₹372,400.00 across 1,064 breaches.
- Transfer cost exposure: ₹370,575.00 across 1,215 transfers.
- Known replacement exposure: ₹3,415,990.00 across 1,896 replacements; missing cost count 0.
- Refund amount exposure: ₹5,350,871.00; refunds are not classified as avoidable.
- Operational cost exposure (contact + SLA credit + transfers): ₹3,996,035.00.
- Total relevant exposure (operational + known replacement + refunds): ₹12,762,896.00. Repeat-contact cost is a subset of contact costs and not added again.
- Refund and replacement anomaly tickets: 6; associated combined exposure ₹25,577.00; escalation flag only, not recoverable savings or misconduct.

## Quarterly view

| Quarter | Tickets | Contact | SLA breach | Transfers | Replacement | Refund | Repeat candidates | Relevant exposure |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-Q1 | 1,029 | ₹284,180 | ₹29,750 | ₹34,770 | ₹166,320 | ₹567,782 | 124 / ₹34,540 | ₹1,082,802 |
| 2025-Q2 | 1,118 | ₹309,110 | ₹37,800 | ₹27,450 | ₹192,690 | ₹562,470 | 164 / ₹43,080 | ₹1,129,520 |
| 2025-Q3 | 1,577 | ₹439,910 | ₹52,850 | ₹53,680 | ₹287,820 | ₹856,957 | 253 / ₹71,700 | ₹1,691,217 |
| 2025-Q4 | 2,517 | ₹702,370 | ₹76,650 | ₹80,520 | ₹554,990 | ₹1,263,771 | 393 / ₹113,910 | ₹2,678,301 |
| 2026-Q1 | 3,442 | ₹943,640 | ₹105,000 | ₹110,105 | ₹1,567,540 | ₹1,215,270 | 641 / ₹175,650 | ₹3,941,555 |
| 2026-Q2 | 2,067 | ₹573,850 | ₹70,350 | ₹64,050 | ₹646,630 | ₹884,621 | 333 / ₹93,290 | ₹2,239,501 |

Latest complete quarter: 2026-Q2. The dataset ends 30 June 2026; no Q3 2026 values are inferred.

## Replacement and claim checks

- Replacement calculation uses product unit cost + ₹340 logistics. Finance's approximate ₹2,500 value was not used. December 2025 exposure was ₹275,880.00; June 2026 was ₹139,970.00; June vs December change -49.26%.
- Festive proxy uses Q4 2025 vs Q3 2025: ticket volume 59.61% and replacement count 94.3%. This is not a year-over-year seasonal test; Q4 2024 is unavailable, so the claim cannot be established.

## Repeat-contact candidates and opportunity

- Detectable repeat-contact candidates: 1,908; subsequent-contact channel cost: ₹532,170.00. These are issue proxies, not complete FCR.
- 10%, 20%, and 30% scenarios are reported per cost driver in `opportunity_scenarios.parquet`; they are hypothetical reductions and not realized savings.

## Limits

- Ticket exposure is not causal attribution; high exposure may reflect ticket mix, workload, or policy-compliant action.
- First-response actor identity is unavailable; SLA is resolver-associated. Transfers may be intentional. Refunds may be policy-valid.
- Repeat-contact matching can miss same-issue contacts and include unrelated issues sharing an order or SKU; candidates only.
- 567 tickets lack effective peer/roster context; unmatched tickets remain in overall totals.
- Refund+replacement anomalies are flagged for review; no source values are rewritten. Unknown replacement unit costs would remain flagged and excluded from known cost totals.
- Elapsed handle time is not converted into paid labor cost. No agent ranking, training score, or recommendation is produced.
