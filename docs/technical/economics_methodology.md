# Stage 4 Economics Methodology

## Policy inputs

All rates come from `data/raw/support-policy.pdf`, version 3.2, section 4 (FY26 planning figures) and section 5 (replacement cost). The centralized implementation is `src/vireo/policy/economics.py`.

| Policy item | Amount | Treatment |
|---|---:|---|
| Chat contact | ₹210 | Per ticket whose documented channel is chat |
| Email contact | ₹260 | Per ticket whose documented channel is email |
| Voice callback contact | ₹520 | Per ticket whose documented channel is voice |
| Social contact | ₹240 | Per ticket whose documented channel is social |
| Blended contact | ₹290 | Reference only; never substituted for a known channel |
| Internal transfer | ₹305 | Per transfer count |
| SLA breach credit | ₹350 | Per Stage 2 `sla_breach_flag` |
| Staffing cost | ₹165 per agent-hour | Recorded as policy context only; not applied to elapsed handle time |
| Replacement logistics | ₹340 | Added once per replacement ticket to product unit cost |

## Ticket calculations and eligibility

- `contact_cost_inr`: channel lookup from `ticket_metrics.channel`; unsupported/missing channels fail validation rather than use the blended value.
- `sla_breach_cost_inr`: ₹350 when `sla_breach_flag` is true, otherwise zero. SLA breach rate uses the `valid_for_sla` population. Average credit per completed ticket divides by resolved plus closed tickets.
- `transfer_cost_inr`: numeric Stage 2 transfer count × ₹305. This is routing/re-handling exposure, not agent fault.
- `replacement_cost_inr`: only when `replacement_issued == Y`; unique product `sku` lookup and `unit_cost_inr + ₹340`. No retail price, order value, quantity multiplier, or refurbishment recovery is used. A missing product/cost is flagged; unknown cost is null and excluded from known totals.
- `refund_amount_inr`: nonnegative source refund amount; blank is zero. `refund_reason_code` is preserved. Refunds are not deemed avoidable.
- `refund_replacement_anomaly_flag`: positive refund and replacement on the same ticket. Its known amount is reported separately for escalation; no recovery or misconduct is inferred.
- `repeat_contact_cost_inr`: channel cost of the subsequent ticket when a detectable repeat candidate is found; this is a subset of contact exposure and is not added a second time to total exposure.

The named `operational_cost_exposure_inr` is contact + SLA credit + transfer. `total_relevant_exposure_inr` is operational + known replacement + refund exposure. The components remain separate because they have different accounting meanings.

## Repeat-contact candidate rule

Tickets are considered a candidate when the same customer has another ticket created strictly after a prior resolution and within 30 days. Matching requires the same nonblank `order_id`; when both order IDs are blank, the same nonblank `product_sku` is used. The nearest prior qualifying resolution is recorded. This is an issue proxy, not the full policy-defined FCR: different issues on one order/SKU can create false positives, while missing order/SKU, changed identifiers, and contacts beyond 30 days can create false negatives. It does not establish that the prior ticket was incorrectly resolved.

## Aggregation and peer context

Ticket grain is preserved. Monthly and calendar-quarter periods use `created_at` converted to configured reporting timezone (Asia/Kolkata by default). Full-period, month, quarter, channel, resolver team/tier, resolved-agent assignment, and Stage 3 peer-group aggregates are available. Agent economics include only completed tickets with an agent ID and describe observed cost exposure associated with the resolved-ticket population. Unmatched roster tickets remain in overall totals and carry no peer group.

Replacement family comes from normalized products. Orders are audited for unique `order_id` but are not joined to economics because replacement cost is defined per replacement ticket and no order quantity multiplier is warranted.

## Scenario opportunity and limits

10%, 20%, and 30% scenario values equal the corresponding fraction of each observed exposure. They are conditional arithmetic examples, not realized savings or causal estimates. Repeat-contact scenario is reported separately as a subset of contact cost and excluded from combined scenario totals to prevent double counting. Refund exposure scenarios do not imply refunds can or should be eliminated.

The source identifies `agent_id` as the resolver, not the first responder; SLA costs cannot be attributed to the resolver as cause. Transfers can be intended routing, refunds/replacements can be policy-compliant, and case mix can differ. The ₹165 staffing rate is not multiplied by Stage 2 elapsed handle time (first response to resolution), because elapsed ticket time is not paid labor time.
