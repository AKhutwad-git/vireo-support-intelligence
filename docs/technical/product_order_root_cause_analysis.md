# Product and Order Root-Cause Analysis

## Scope

- Ticket population: 11,750; rows preserved: True.
- Order links: 10,817 matched (92.1%), 933 ambiguous, 0 unmatched.
- Replacements: 1,896; 89.7% link to a matched order.
- Minimum support: At least 30 eligible tickets for replacement-rate display; CSAT means show their response denominator, and no significance is implied.

## Product/SKU findings

Observed SKU aggregates; rates use eligible Y/N flags and CSAT means use completed valid responses.

| SKU | Tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |
|---|---:|---:|---:|---:|---:|---:|---:|
| VA-EB-PL2 | 4,402 | 4,402 | 1,166 | 26.5% | ₹2,122,120 | 1,854 | 3.07 |
| VA-EB-PL1 | 1,255 | 1,255 | 146 | 11.6% | ₹213,160 | 512 | 3.53 |
| VA-HP-ST2 | 327 | 327 | 38 | 11.6% | ₹92,720 | 141 | 3.40 |
| VA-NB-ARC | 382 | 382 | 43 | 11.3% | ₹37,840 | 182 | 3.52 |
| VA-EB-AIR | 1,005 | 1,005 | 111 | 11.0% | ₹122,100 | 428 | 3.53 |

### Replacement exposure leaders

| SKU | Tickets | Replacements | Exposure |
|---|---:|---:|---:|
| VA-EB-PL2 | 4,402 | 1,166 | ₹2,122,120 |
| VA-SW-NX2 | 1,047 | 101 | ₹281,790 |
| VA-EB-PL1 | 1,255 | 146 | ₹213,160 |
| VA-HP-ST3 | 772 | 70 | ₹209,300 |
| VA-EB-AIR | 1,005 | 111 | ₹122,100 |

### VA-EB-PL2 check

Observed VA-EB-PL2: 4,402 tickets; 4,402 eligible; 1,166 replacements (26.5%); ₹2,122,120 exposure; 1,854 completed valid CSAT responses; mean 3.07/5.
Other SKUs: 7,348 tickets; 7,348 eligible; 730 replacements (9.9%); ₹1,293,870 exposure; 3,093 valid CSAT responses; mean 3.48/5.

## Order-channel findings

| Order channel | Tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |
|---|---:|---:|---:|---:|---:|---:|---:|
| Amazon | 3,323 | 3,323 | 516 | 15.5% | ₹933,670 | 1,358 | 3.38 |
| Flipkart | 1,517 | 1,517 | 235 | 15.5% | ₹419,320 | 652 | 3.31 |
| vireo.in | 5,977 | 5,977 | 949 | 15.9% | ₹1,706,780 | 2,557 | 3.33 |

## Lot findings

31 lots meet the 30 eligible-ticket floor; 1,036 additional observed SKU-lot groups are below that floor and omitted from rate comparisons. Lot rates are descriptive and do not imply manufacturing causality.

| SKU | Lot | Tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| VA-EB-PL2 | PL2-2511-3 | 199 | 199 | 85 | 42.7% | ₹154,700 | 82 | 2.63 |
| VA-EB-PL2 | PL2-2510-1 | 222 | 222 | 88 | 39.6% | ₹160,160 | 88 | 2.67 |
| VA-EB-PL2 | PL2-2511-2 | 182 | 182 | 72 | 39.6% | ₹131,040 | 66 | 2.83 |
| VA-EB-PL2 | PL2-2510-4 | 218 | 218 | 85 | 39.0% | ₹154,700 | 90 | 2.53 |
| VA-EB-PL2 | PL2-2512-4 | 146 | 146 | 56 | 38.4% | ₹101,920 | 61 | 2.79 |
| VA-EB-PL2 | PL2-2510-3 | 221 | 221 | 84 | 38.0% | ₹152,880 | 88 | 2.73 |
| VA-EB-PL2 | PL2-2511-4 | 218 | 218 | 81 | 37.2% | ₹147,420 | 90 | 2.86 |
| VA-EB-PL2 | PL2-2510-2 | 211 | 211 | 77 | 36.5% | ₹140,140 | 97 | 2.71 |
| VA-EB-PL2 | PL2-2512-2 | 144 | 144 | 52 | 36.1% | ₹94,640 | 55 | 2.87 |
| VA-EB-PL2 | PL2-2511-1 | 188 | 188 | 67 | 35.6% | ₹121,940 | 69 | 2.71 |

## Agent exposure

90 agent-product combinations meet the 30 eligible-ticket floor. The table is exposure context only; it is not an agent ranking or training input.

| Agent | SKU | Tickets | Share of SKU tickets | Eligible | Replacements | Rate | Exposure | CSAT n | Mean CSAT |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A3044 | VA-EB-PL2 | 146 | 3.3% | 146 | 90 | 61.6% | ₹163,800 | 62 | 2.11 |
| A3042 | VA-EB-PL2 | 133 | 3.0% | 133 | 83 | 62.4% | ₹151,060 | 61 | 2.07 |
| A3004 | VA-EB-PL2 | 162 | 3.7% | 162 | 82 | 50.6% | ₹149,240 | 66 | 2.45 |
| A3040 | VA-EB-PL2 | 139 | 3.2% | 139 | 82 | 59.0% | ₹149,240 | 59 | 2.05 |
| A3043 | VA-EB-PL2 | 130 | 3.0% | 130 | 79 | 60.8% | ₹143,780 | 50 | 2.18 |
| A3041 | VA-EB-PL2 | 141 | 3.2% | 141 | 77 | 54.6% | ₹140,140 | 58 | 2.03 |
| A3039 | VA-EB-PL2 | 129 | 2.9% | 129 | 74 | 57.4% | ₹134,680 | 55 | 2.27 |
| A3006 | VA-EB-PL2 | 132 | 3.0% | 132 | 68 | 51.5% | ₹123,760 | 58 | 2.36 |
| A3005 | VA-EB-PL2 | 150 | 3.4% | 150 | 66 | 44.0% | ₹120,120 | 63 | 2.52 |
| A3007 | VA-EB-PL2 | 142 | 3.2% | 142 | 60 | 42.3% | ₹109,200 | 64 | 2.72 |
| A3029 | VA-EB-PL2 | 121 | 2.7% | 121 | 27 | 22.3% | ₹49,140 | 53 | 2.96 |
| A3027 | VA-EB-PL2 | 127 | 2.9% | 127 | 26 | 20.5% | ₹47,320 | 59 | 3.10 |
| A3031 | VA-EB-PL2 | 141 | 3.2% | 141 | 24 | 17.0% | ₹43,680 | 61 | 3.38 |
| A3019 | VA-EB-PL2 | 93 | 2.1% | 93 | 23 | 24.7% | ₹41,860 | 40 | 3.40 |
| A3024 | VA-EB-PL2 | 152 | 3.5% | 152 | 21 | 13.8% | ₹38,220 | 70 | 3.46 |
| A3037 | VA-EB-PL2 | 169 | 3.8% | 169 | 21 | 12.4% | ₹38,220 | 65 | 3.32 |
| A3028 | VA-EB-PL2 | 100 | 2.3% | 100 | 19 | 19.0% | ₹34,580 | 46 | 3.26 |
| A3030 | VA-EB-PL2 | 99 | 2.2% | 99 | 19 | 19.2% | ₹34,580 | 42 | 3.26 |
| A3018 | VA-EB-PL2 | 90 | 2.0% | 90 | 18 | 20.0% | ₹32,760 | 38 | 3.79 |
| A3020 | VA-EB-PL2 | 107 | 2.4% | 107 | 16 | 15.0% | ₹29,120 | 45 | 3.44 |

Across agents, 43 of 44 handled at least 30 eligible VA-EB-PL2 tickets. Their observed within-SKU replacement rates range from 0.0% to 62.4% over 32–169 tickets; the largest individual share is 3.8% of PL2 tickets. These unadjusted differences require case and policy review and do not establish agent fault.

## Interpretation

**Observed:** product, order-channel, lot, and agent-product differences are measurable in this supplied population using the denominators above.

**Possible explanation:** the PL2 SKU/lot pattern is a strong operational investigation lead, while the broadly distributed product exposure and within-SKU differences indicate product mix alone may not explain every agent outcome. Review product/lot evidence and ticket handling before making agent-specific decisions.

**Not established:** causality, product defects, agent fault, avoidable costs, or guaranteed savings. The analysis does not alter peer comparisons or training decisions.

## Reproducible artifacts

- `data/outputs/product_order_root_cause.csv`: combined SKU, family, order-channel, supported lot, and agent-product aggregates.
- `data/interim/ticket_order_enriched.parquet`: internal one-row-per-ticket linkage and flags; it is not included in dashboard bundles.
- `data/interim/product_order_root_cause_summary.json` and the Stage 4 report: coverage, definitions, support thresholds, and aggregate outputs.
- `data/interim/product_sku_analysis.parquet`, `product_family_analysis.parquet`, `order_channel_analysis.parquet`, `product_lot_analysis.parquet`, and `agent_product_exposure.parquet`: dashboard aggregate tables.
