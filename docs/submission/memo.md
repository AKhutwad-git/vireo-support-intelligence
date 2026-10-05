# Banao Technologies Evaluation Memo

## Product

Vireo Support Intelligence is a deterministic support analytics and decision-support application. It consolidates ticket, roster, product, policy, and cost inputs; calculates operational measures; compares agents within Tier-safe peers; and surfaces evidence-gated training priority with economic context. A Streamlit dashboard presents the generated outputs and downloadable tables.

## Verified results

- Reporting population: 11,750 tickets, January 2025 through June 2026; latest available quarter: 2026 Q2.
- 11,183 completed tickets; 4,947 completed-ticket CSAT responses; mean CSAT 3.33/5.
- Median elapsed handle time: 29 minutes; SLA breaches: 1,064 (9.1%); transfers: 1,215.
- Stage 4 observed exposure: ₹3,253,060 contact, ₹3,415,990 replacement, and ₹5,350,871 refund exposure. These are separate observed categories and are not agent-caused costs or guaranteed savings.
- Stage 6: 0 agents meet the default evidence threshold for a defensible training recommendation; 44 are monitor.
- Stage 7: all 12 independent reconciliations and eight synthetic decision scenarios passed; 220 explanation checks passed; deterministic reruns matched.

## Decision and limitations

The client request for a bottom-ten list is not supported by current uncertainty evidence. The default decision gate was retained. Point-estimate-only sensitivity surfaced A3015, A3021, and A3026 as exploratory examples only; none is recommended.

Stage 3 intervals are approximate and assume independent tickets. Clustered case-mix uncertainty, genuine out-of-time validation, and ground-truth agent-quality error measurement are not available. Stage 5 is partial: there are no real model predictions, model-quality evaluation, or real usage-cost measurements. 567 tickets lack effective roster context. Handle-time outliers are retained. SLA is associated with resolver identity because first-responder identity is unavailable.

## Readiness

The deterministic analytical outputs and presentation layer are validated for this supplied source pack. Stage 7 verdict: **VALIDATED WITH MATERIAL LIMITATIONS**. This is an evaluation deliverable, not production deployment approval. No causal personnel finding or realized financial savings is claimed.
