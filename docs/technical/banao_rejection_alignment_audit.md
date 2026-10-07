# Banao Rejection Feedback — Root-Cause Alignment Audit

Audit date: 2026-10-07
Historical point-in-time scope: this audit predates the Product & Orders remediation. Its findings about missing product/order outcome analysis describe the repository at audit time, not the current candidate. The implemented analysis and current findings are in `product_order_root_cause_analysis.md`.
Scope: evidence-only review of the current repository, existing generated artifacts, and supplied source pack. No application code, tests, source data, dashboard, or prior documentation was changed. No pipeline, test suite, or AI evaluation was rerun. A few read-only group-bys over existing canonical Parquet outputs are explicitly labeled below as audit-only checks; they were not saved as product outputs.

## Executive verdict

**PARTIALLY ALIGNED — the reviewer identified a genuine missing business analysis, while overlooking some product-aware work that already exists.**

The project did not ship a product/order root-cause analysis for CSAT and replacement outcomes. It did, however, use product family in agent case-mix adjustment and already created a replacement-only SKU/family exposure table. Thus, “no product work at all” would be too broad; “no surfaced product/order diagnosis explaining the poor outcomes” is accurate.

A read-only audit check on the existing ticket metrics found a strong descriptive product signal: SKU `VA-EB-PL2` had 1,166 replacements among 4,402 tickets (26.5%) and mean completed-ticket CSAT 3.07/5 across 1,854 responses. Other SKUs combined had 730/7,348 replacements (9.9%) and mean CSAT 3.48/5 across 3,093 responses. This is an observational signal, not proof that the product caused low CSAT or replacement decisions. The existing product report did not compute those denominators or CSAT summaries, and neither the dashboard nor memo surfaced this signal.

## Data sources and availability

| Source | Path | Relevant keys and fields | Joinable to | Coverage and missingness |
|---|---|---|---|---|
| Tickets | `data/raw/tickets.csv`; canonical `data/interim/normalized_tickets.parquet` and `ticket_metrics.parquet` | `ticket_id`; `customer_id`; nullable `order_id`; `product_sku`; `agent_id`; created/first-response/resolved timestamps; channel, intake category, priority, first-routed team; CSAT, refund amount/reason, replacement flag; messages and notes | Customers, orders, products, roster, ticket economics | 11,750 unique tickets. `order_id` blank on 4,107 (34.95%); CSAT blank on 6,554 (55.78%); refund amount/reason blank on 9,881 (84.09%); resolved timestamp blank on 567 (4.83%). Primary CSAT uses 4,947 completed-ticket responses; 249 populated open/pending scores are excluded. 1,896 replacement flags are `Y`; 1,869 tickets have positive refund amounts. Four channels, 11 categories, three priority values. |
| Agent roster | `data/raw/agents.csv`; canonical `data/interim/normalized_agents.parquet` | `agent_id` plus effective dates, team, tier, site, shift; display name is not a safe key | Tickets by `agent_id` and effective ticket time | 44 unique IDs/44 roster rows; 43 distinct display names. The source email warns about duplicate names. 567 tickets lack effective roster context, mostly because no usable resolution-time assignment is available. |
| Customers | `data/raw/customers.csv`; canonical `data/interim/normalized_customers.parquet` | `customer_id`; signup date, city, state, care-plus flag | Tickets and orders by `customer_id` | 9,500 rows, 9,500 unique IDs. Every ticket customer ID and every order customer ID matched in the current data. Customer attributes are not used in peer adjustment or a customer-level root-cause analysis. |
| Orders | `data/raw/orders.csv`; canonical `data/interim/normalized_orders.parquet` | `order_id`; `customer_id`; `sku`; order date, sales channel, quantity, order value, manufacturing lot code | Tickets by direct `order_id` or unique `customer_id + product_sku`; customers; products by SKU | 15,500 unique order IDs. Customer and SKU keys are populated and all 15,500 rows match the customer/product dimensions. 1,271 distinct lot codes. The order date/channel/quantity/value/lot fields are not brought into the current CSAT/replacement decision analysis. |
| Products | `data/raw/products.csv`; canonical `data/interim/normalized_products.parquet` | `sku`; product name, family, launch date, unit cost, retail price, warranty months | Tickets by `product_sku`; orders by `sku` | 14 unique SKUs, five product families; every ticket SKU and order SKU matches a product row. Product fields are available for product-family adjustment and replacement unit-cost calculation. Warranty term is present; ticket-level warranty status is not. |
| Policy | `data/raw/support-policy.pdf`; interpreted in `src/vireo/policy/economics.py` | Support policy, cost and eligibility rules | Not a data join | PDF is present but was not text-extracted in the forensic run. The implemented replacement-cost rule is product unit cost + ₹340 logistics per replacement. |
| CSAT, refund, replacement and time outcomes | Stored on `tickets.csv` and carried to `ticket_metrics.parquet` / `ticket_economics.parquet` | Ticket ID is the event key; product/order/agent keys are available on the ticket | Product/agent/order groupings are technically possible where links resolve | CSAT is a ticket survey score; refund and replacement are ticket-level fields. There is no separate replacement event timestamp or replacement-history table, so before/after-replacement CSAT cannot be established. Ticket timestamps are normalized; helpdesk naive times are interpreted as IST and legacy reconstructed `resolved_at` as UTC. |

## Ticket → customer → order → product linkage

The data does support a mostly joinable path, but the analytical workflow does not carry the full order detail through to outcome analysis.

| Join | Implementation / artifact | Rows before → after | Match rate and unmatched rows | Analytical use and outcome impact |
|---|---|---:|---|---|
| Ticket → customer (`customer_id`) | `src/vireo/pipeline/preprocess.py`; canonical ticket/customer tables | 11,750 → 11,750 | 11,750/11,750 (100%); 0 unmatched | Used to inspect signup/order anomalies. Customer city, state, care-plus and history do not affect peer ranking or CSAT/replacement analysis. |
| Ticket → order, direct (`order_id`) | `src/vireo/pipeline/preprocess.py`; `order_match_flag` in normalized tickets | 11,750 ticket rows retained; 7,643 have an order ID | 7,643/7,643 populated IDs match (100% of populated IDs; 65.05% of all tickets). All 7,643 direct matches also agreed on ticket/order customer and SKU in this audit. | Used to check order-match/signup anomalies and in repeat-contact matching. Order date, order channel, quantity, value and lot are not joined into Stage 4 outcome tables. Does not directly affect CSAT or agent ranking. |
| Ticket → order, unique fallback (`customer_id + product_sku`) | `src/vireo/pipeline/preprocess.py`; also analogous same-customer/SKU repeat-contact fallback | Applied where the direct ID did not resolve; ticket grain retained | 3,174 unique fallback matches; 933 ambiguous candidate sets; 0 with no candidate. Total resolved ticket-order links: 10,817/11,750 (92.06%); 933/11,750 (7.94%) remain ambiguous/unmatched. | Fallback is used for anomaly/match status and repeat-contact proxy, not for joining order economics or CSAT. Ambiguous cases are correctly not assigned an arbitrary order. |
| Order → customer (`customer_id`) | Stage 1 relationship validation; raw/canonical order and customer tables | 15,500 → 15,500 order rows | 15,500/15,500 (100%); 0 unmatched | Relationship is validated, but order/customer attributes are not enriched into ticket outcome analysis. |
| Ticket → product (`product_sku` → `sku`) | `src/vireo/analytics/comparisons.py` → `src/vireo/analytics/case_mix.py:add_product_family`; `src/vireo/analytics/economics.py` | 11,750 → 11,750 | 11,750/11,750 (100%); 0 unmatched | Product family is attached for Stage 3 case-mix distribution and adjustment. Stage 4 uses SKU/product unit cost for replacement tickets. Family is not a CSAT-by-product deliverable. |
| Order → product (`sku`) | Stage 1 relationship validation; source/canonical tables | 15,500 → 15,500 order rows | 15,500/15,500 (100%); 0 unmatched | Key relationship is validated, but an enriched order→product table is not used for product/order root-cause analysis. |
| Ticket → effective agent roster | `src/vireo/data/temporal.py`; Stage 2/3 artifacts | 11,750 → 11,750 ticket grain | 11,183 effective context matches; 567 unmatched (95.17% / 4.83%) | Used for agent metrics and Tier-safe peer comparisons. Agent ID is the join key; team/tier/site/shift form peer context. |

There is no saved analytical join of each ticket to its full order record and then to product/order characteristics. The 10,817 resolvable ticket-order links make such analysis feasible for most tickets; the remaining 933 must stay explicitly unresolved. The product link is complete by SKU independently of order linkage.

## Replacement analysis

### What exists

- `src/vireo/analytics/economics.py` calculates ticket-grain replacement exposure from product unit cost + ₹340 logistics and preserves ticket, customer, order ID, SKU, and agent ID.
- `data/interim/product_economics.parquet` has 14 rows grouped by replacement SKU/family. It contains replacement count and replacement exposure by product; it is built from replacement tickets only.
- Existing Stage 4 totals are 1,896 replacements and ₹3,415,990 exposure, with no missing replacement product costs.
- The existing SKU table shows `VA-EB-PL2`: 1,166 replacement tickets and ₹2,122,120 exposure, about 61.5% of replacements and 62.1% of replacement exposure. This is product concentration by count/exposure, not an unusually high *rate* because the table has no all-ticket SKU denominator.
- `ticket_economics` retains `order_id`, `product_sku`, customer and agent IDs, but it does not contain joined order date, order sales channel, quantity, order value or lot code. The Overview/dashboard bundle does not load or display `product_economics.parquet`.

### Audit-only rate/CSAT check (not an existing persisted product finding)

To test whether the source has an observable pattern, a read-only group-by of existing `ticket_metrics.parquet` and `ticket_economics.parquet` was made for this audit. No pipeline was rerun and no output dataset was written.

| SKU population | Tickets | Replacements | Replacement rate | Completed CSAT responses | Mean CSAT |
|---|---:|---:|---:|---:|---:|
| `VA-EB-PL2` | 4,402 | 1,166 | 26.5% | 1,854 | 3.07/5 |
| All other SKUs | 7,348 | 730 | 9.9% | 3,093 | 3.48/5 |

This is a substantial descriptive lead for follow-up, not causal proof. It is not a corrected/multivariable comparison and does not control for channel, priority, quarter, order source, customer, issue severity or agent assignment. It does not establish that PL2 caused replacements or low CSAT. The reviewer was right that the submitted workflow failed to surface and investigate this product concentration; the evidence does not yet establish the “real driver.”

### Orders and concentration not examined

Of the 1,896 replacement tickets, 1,215 had direct order IDs and 485 more had a unique customer+SKU fallback, for 1,700/1,896 (89.7%) with a resolvable order; 196 replacement cases were ambiguous. The current Stage 4 did not examine replacement by order, order sales channel, lot, order date/age, quantity, value, or customer history. It did not report rates by order population or top lots/orders. Product-family/SKU replacement count and exposure are the only existing product cut. Refunds are grouped by reason code in `refund_reason_economics.parquet`, not by product/order with CSAT.

## CSAT and root-cause analysis

| Requested analysis | Existing implementation evidence | Status |
|---|---|---|
| CSAT by product SKU/family | No saved output groups CSAT by SKU or family. `case_mix_metrics.parquet` reports product-family ticket shares, not CSAT outcomes. | MISSING as a product/root-cause analysis |
| Product family as an agent-comparison control | Stage 3 attaches family from `product_sku` for every ticket and standardizes within channel × priority × quarter × product-family work cells, with documented fallback. All estimates remain Tier-safe. | PARTIAL and real safeguard |
| CSAT by replacement/refund/warranty | No saved cross-tab or model. Audit-only aggregate check: replacement tickets had 794 completed CSAT responses, mean 2.67; other tickets had 4,153, mean 3.45. This compares ticket outcomes and is not before/after evidence. | MISSING in the product; limited audit signal only |
| CSAT by product × agent/channel/priority | No saved outcome table or dashboard view; product-family mix distributions by agent are descriptive only. | MISSING |
| CSAT before/after replacement | No separate replacement event time/history. | DATA/LINKAGE LIMITATION |
| CSAT/refund/replacement by order or lot | Order channel, value and lot exist, but there is no joined outcome table or saved analysis. | DATA AVAILABLE / ANALYSIS MISSING |

The single-ticket CSAT score and replacement flag do not tell whether a customer rated the service before or after receiving a replacement. The source also lacks a dedicated warranty claim/status field. Product warranty months exist, but purchase date/order matching and warranty eligibility are not analyzed together.

For the delivered product, product-specific CSAT/order root-cause analysis is **MISSING — not implemented**. The order source fields exist, so the order-channel/lot outcome cuts are **DATA AVAILABLE / ANALYSIS MISSING**. A before/after replacement comparison is a **DATA/LINKAGE LIMITATION** because a separate replacement event date is absent.

## Agent comparisons and product/order controls

The actual Stage 3 adjustment includes channel, priority, calendar quarter and product family within Tier-safe peer cohorts. Peer cohort selection uses effective roster tier/team/site/shift and falls back in a fixed hierarchy. The Stage 6 evidence gate then requires adverse adjusted intervals and evidence/coverage gates. It does not adjust for ticket `assigned_team` as a work-cell feature, SKU/model, order retailer/channel, lot, order age/value/quantity, customer/order history, replacement, refund, or warranty status. Replacement/refund are post-routing outcomes and are correctly excluded as peer-adjustment predictors; however, their product/order causes were not separately diagnosed.

| Variable | Present in data? | Used in peer adjustment? | Used in root-cause analysis? |
|---|---|---|---|
| Channel | Yes, on tickets | Yes | No product/order outcome analysis by channel |
| Priority | Yes, on tickets | Yes | No product/order outcome analysis by priority |
| Quarter | Yes, derived from ticket time | Yes | Exposure trend exists by quarter; no product/order × quarter root cause |
| Product family | Yes; SKU maps to five families | Yes, family-level | Replacement SKU/family count/exposure exists; CSAT family outcome analysis missing |
| Product/model/SKU | Yes, 14 SKUs | No; only family is an adjustment feature | Replacement counts/exposure by SKU exist; rates and CSAT by SKU are not saved/surfaced |
| Replacement | Yes, ticket flag | No; outcome field | Aggregate exposure and SKU count; not linked to order/CSAT in the product |
| Refund | Yes, ticket amount/reason | No; outcome field | Overall exposure/reason-code grouping; no product/order/CSAT linkage |
| Warranty / hardware queue | Warranty duration and team fields exist; no explicit ticket warranty status | Not directly; roster team is peer context, not the ticket's assigned queue | No product×warranty/queue outcome analysis |
| Order characteristics | Yes: channel, lot, date, quantity, value | No | No saved analysis by these dimensions |
| Customer/order history | Customer and order IDs/history fields exist; repeat-contact proxy uses same customer/order or customer/SKU | No | Repeat-contact candidates only; no customer/order root-cause segmentation |

Accordingly, the current analysis could partially control for product *family* and detect product-SKU replacement volume/exposure, but it could not explain product-specific CSAT or lot/order concentration, nor test product-SKU × agent exposure in the delivered decision flow. The one-off audit check above demonstrates that a useful SKU signal was available from the local data.

## Did the implementation prioritize agents before causes?

Yes. Stage 2 summarizes CSAT/handle time by agent; Stage 3 compares agents; Stage 6 makes an agent training decision; and the current dashboard adds Bottom 10 and Top 5 agent review queues. Product-family case mix is a meaningful safeguard inside those comparisons, but the project did not first publish product/order-level CSAT and replacement drivers. This left the reviewer with agent lists and aggregate rupee totals rather than a clear product/order explanation.

Both statements are true: the interval gate prevented converting point estimates into a training recommendation (0 defensible training candidates; 44 monitors), and the delivered product still missed the requested operational root-cause diagnosis. The descriptive Top 5/Bottom 10 lists remain explicitly review-only, not bonus/training decisions. Keeping this gate is still appropriate.

## Original business question coverage

| Original context / request | Current answer |
|---|---|
| CSAT and handle time per agent; join on `agent_id` | Implemented; IDs are used, and display names are not join keys. |
| Bottom ten for Q3 training; ₹4 lakh budget | Stage 6 returns 0 defensible candidates / 44 monitored; budget decision is ₹0 agent-specific retraining and reserve ₹4,00,000. Bottom 10 remains a review queue, not a personnel recommendation. |
| Top five Diwali bonus | Top 5 is a review list; no bonus determination is made. |
| About 40 IVR-junk messages | Heuristic flags 21 while email estimates about 40; explicitly documented as under-detection/limitation. |
| Helpdesk timestamps displayed in IST | Naive helpdesk timestamps are interpreted as IST; legacy reconstructed resolution timestamps have a separate UTC rule. |
| No full-corpus AI calls | No full-corpus inference; the later controlled AI evaluation made 20 requests on 20 reviewed cases, with only 3 schema-valid outputs. |
| Hardware triage/warranty may bias agent ranking | Tier-safe team context and product-family adjustment reduce some confounding, but ticket first-routed `assigned_team`, SKU and warranty status are not fully controlled. |
| Replacement cost = unit cost + ₹340 | Implemented for known SKU replacements. The approximate ₹2,500 claim was rejected. |
| What drives poor CSAT/replacement; agent or difficult order population? | Not answered in the delivered memo/dashboard. Some product family/SKU context exists; order detail and outcome root-cause analysis are missing. |

The original email says “Dashboard first, causes later,” but the rejection establishes that the final review expected at least a first-pass product/order pattern analysis. The source pack contains enough product detail and mostly resolvable order links to perform that bounded analysis.

## Memo audit

File: `docs/submission/memo.md` (about 550 words).

1. **Leads with decision:** No. It opens with a product description, not the ₹0 agent retraining / ₹4,00,000 reserve decision and the main observed driver question.
2. **Rupee impact:** Yes, it gives ₹3,253,060 contact, ₹3,415,990 replacement and ₹5,350,871 refund exposure, and correctly labels these as observed/non-causal. These figures are not used to lead the memo.
3. **₹4 lakh decision:** Yes; ₹0 goes to agent-specific retraining and ₹4,00,000 is reserved.
4. **Business goal:** Yes; 9.06% to 8.06%, with ₹41,125 same-population policy-credit sensitivity and caveats.
5. **Why agents were not automatically blamed:** Yes; the gate, Tier-safe comparisons, uncertainty, and 0/44 decision are explained.
6. **Product/order root causes:** No. No product SKU/order finding appears.
7. **Conciseness:** At about 550 words it is not excessively long for an 11-minute review, but the structure is not decision-first and spends its opening on product/method context.
8. **Observed vs projected economics:** Yes; exposure and sensitivity are clearly distinguished from savings/causality.
9. **Methodology detail:** Moderate. It includes validation and AI caveats, but no unnecessary model or implementation narrative dominates. The larger gap is missing diagnosis and decision-first ordering, not an overly technical memo.

## Time-limit audit

The submission form records **approximately 20 hours**, explicitly as a retrospective estimate rather than tracked time. The task context provided for this audit describes an approximately five-hour take-home, so the estimate is about four times that target. No time log or per-stage allocation is present; exact overrun or allocation cannot be attributed.

The repository demonstrates work beyond the core dashboard/business analysis: deployment packaging, Docker runtime, release manifests, health checks, CI, production operations/incident-response documentation, robustness/evaluation stages, and extensive tests. Thoroughness itself is not the issue; compared with the feedback, the clearest scope imbalance is that the work built substantial release/operational validation while not delivering the small product/order root-cause analysis. There is no evidence to claim how many of the 20 hours went to any one area.

## Requirement matrix

| Reviewer feedback | Evidence in repo | Status | Gap |
|---|---|---|---|
| Join tickets to order details | Direct `order_id` match for 7,643; unique customer+SKU fallback resolves 3,174 more; 933 are ambiguous. Preprocess uses order data for flags, but does not carry order channel/date/lot/value into outcome analysis. | PARTIAL | The relationship is mostly available but no full order enrichment or root-cause grouping is shipped. |
| Join orders to product details | Order `sku` matches product dimension for 15,500/15,500; relationship validation exists. | PARTIAL | Key relationship is validated, but order-product attributes are not enriched into analytical outputs. |
| Trace replacement problems to products/orders | Replacement-only 14-row SKU/family count/exposure artifact; no denominator/rate, order/lot/channel analysis, or product dashboard. | PARTIAL | Some product concentration exists; no rate-normalized order/source diagnosis. |
| Trace CSAT problems to products/orders | Family controls case-mix adjustment; no CSAT by SKU/family/order/replacement in saved product output or dashboard. | PARTIAL | A product-signal spot check is possible from current data but was not communicated or made part of the analysis workflow. |
| Identify root cause before judging agents | Agent metrics/peer comparison/queues are prominent; family adjustment is partial; Stage 6 refuses unsupported personnel action. | PARTIAL | Root cause remains unidentified, even though automatic blame was prevented. |
| Keep bottom-ten decision evidence-gated | Stage 6 has 0 defensible candidates and 44 monitors; Bottom 10 is explicitly review-only and not a training recommendation. | COMPLETE | Keep the gate; product review should be added alongside it. |
| Lead memo with decision | `memo.md` begins with “Product” and a solution description. | MISSING | Open with the decision and immediate rupee context. |
| Lead with rupee impact | Aggregate observed exposure is present in bullets but not at the beginning and has no product/order driver. | PARTIAL | Bring the key exposure and caveat into the opening decision summary. |
| Stay within time limit | Honest retrospective estimate is ~20 hours; task context says ~5-hour take-home; infrastructure and release work is extensive. | MISSING | No timed records; work appears over scope, with product/order analysis displaced. |

## Most important finding

**What the reviewer got right:** We did not ship the requested product/order root-cause story. The submitted memo/dashboard lacked CSAT and replacement rates by product/order characteristics, despite mostly joinable source data. A read-only audit check finds a pronounced PL2 product signal that should have been investigated and communicated.

**What the reviewer may have misunderstood:** The code did not ignore products entirely. Stage 3 controls for product family, and Stage 4 groups replacement volume/cost by product SKU/family. The implementation refused to label point-estimate agent differences as training evidence. The missing item is full diagnosis and communication, rather than all product linkage being absent.

**What our implementation actually missed:** Full ticket→order→product enrichment in outcome analysis; replacement-rate denominators and order/lot/source attribution; CSAT by product and replacement/order cohort; product×agent exposure; and a short memo that leads with the decision and rupees. The project used product family to make agent comparisons fairer but did not turn available SKU/order signals into an operational root-cause finding.

## Final audit answers

- **Overall verdict:** PARTIALLY ALIGNED.
- **Reviewer feedback confirmed:** YES — the delivered workflow missed product/order root-cause analysis and failed to surface the available PL2 concentration signal.
- **Reviewer feedback not fully confirmed:** Some product analysis exists: family-level adjustment and replacement-only SKU/family count/exposure. The reviewer’s claim would be too strong if read as “no product field or product grouping was used.”
- **Can the data establish ticket → customer → order → product?** Partial. Ticket→customer and ticket/order→product keys resolve 100%; direct/unique-fallback ticket→order linkage resolves 10,817/11,750 (92.06%), while 933 ambiguous tickets remain. For replacement tickets, 1,700/1,896 (89.7%) have a resolvable order.
- **Replacement → product/order:** PARTIAL.
- **CSAT → product/order:** PARTIAL (family is a peer-adjustment control; direct outcome/root-cause analysis is missing).
- **Product exposure → agent ranking:** PARTIAL (family-level case mix controls comparisons; SKU/order exposure interactions are missing).
- **Agent ranking:** The evidence-gated approach remains appropriate. Keep all 44 under monitoring absent defensible adverse evidence; treat Bottom 10 and Top 5 as review queues only.
- **Memo status:** It has the budget decision, numeric goal, observed rupee exposures and caveats, but it does not open with the decision/rupees and contains no product/order root cause.
- **Recommended next step — smallest set:** (1) Add one bounded, row-count-safe order enrichment using direct order IDs and only unique customer+SKU fallbacks; leave ambiguous matches unresolved. (2) Produce a focused SKU/family and order-channel/lot summary with ticket and order denominators, replacement rate/exposure, CSAT response count/mean, and key channel/priority/quarter slices; show agent exposure only as context. (3) Rewrite only the memo opening to lead with that observed signal, the ₹4 lakh decision and explicit non-causal caveats. Do not relax the evidence gate or make training/bonus recommendations from the review queues.
