# Memo to Priya Raman

## Decision

Do not direct the Q3 training reserve to agent-specific retraining on this evidence. The decision engine finds **0 defensible training candidates** and keeps all **44 agents under monitoring**. The Bottom 10 and Top 5 are management review queues, not retraining or bonus decisions.

## Rupees

The proposed operational goal is to reduce the resolver-associated first-response SLA breach rate by **1 percentage point**, from **9.06% (1,064/11,750)** to **8.06%** on a comparable population. On the same ticket denominator, that is about **118 fewer breach events** and **₹41,125** in policy-credit context at ₹350 per breach. This is a same-population sensitivity, not a forecast or savings claim.

The analysis records **₹3,253,060 contact exposure**, **₹3,415,990 replacement exposure**, and **₹5,350,871 refund exposure** as separate observed categories. They are not agent-caused costs or guaranteed savings. Training costs are unavailable, so no training ROI is calculated.

## Product and order finding

VA-EB-PL2 had **1,166 replacements among 4,402 eligible tickets (26.49%)**, compared with **730/7,348 (9.93%)** for other SKUs. Completed-ticket CSAT was **3.07/5 (1,854 responses)** for PL2 and **3.48/5 (3,093 responses)** for other SKUs. **31 lots** meet the 30-ticket support floor for descriptive comparison. Amazon, Flipkart, and vireo.in replacement rates are similar, at **15.5%–15.9%**. Order linkage matched **10,817/11,750 tickets**; **933** remained ambiguous.

## Action

Investigate PL2 product and lot records, warranty handling, and order history before assigning training spend. Keep **₹400,000 reserved** and allocate **₹0** to agent-specific retraining unless stronger agent-specific evidence emerges. The review queues can guide human review but do not change the evidence gate.

## Attribution and evidence limits

PL2 exposure is broad: 43 of 44 agents handled at least 30 PL2 cases. The observed product, lot, and agent-product patterns are investigation leads; they do not establish a manufacturing defect, agent fault, avoidable cost, or causality. The data identifies the resolver, not necessarily the first responder, so SLA is resolver-associated.

The deterministic analysis passed 12 metric reconciliations, eight synthetic decision scenarios, 220 explanation checks, and reproducibility checks. Stage 7 remains **VALIDATED WITH MATERIAL LIMITATIONS**: uncertainty intervals are approximate, clustered case-mix uncertainty and genuine out-of-time validation are absent, and there is no agent-quality ground truth. The bounded Gemini evaluation attempted 20 requests; only 3 produced schema-valid predictions, and all 3 matched their labels. Five failed schema validation and 12 received HTTP 429. The 3/3 result is not overall accuracy; model quality and billed cost are not established.
