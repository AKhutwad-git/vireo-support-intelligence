# Stage 2 Findings

Generated from Stage 1 canonical Parquet inputs. These are descriptive metrics only; no ranking or training decision is made.

## Coverage

- Tickets: 11,750 metric rows.
- Ticket creation date range (IST): 2025-01-01 through 2026-06-30.
- The latest available period is determined from the supplied tickets; no Q3 2026 data is inferred.
- Completed attendance: 11,183 (10,138 resolved + 1,045 closed); open/pending: 567.
- CSAT: 4,947 eligible completed-ticket responses / 11,183 completed tickets; response rate 44.24%; mean 3.33 on the 1–5 scale.
- Populated valid scores on open/pending tickets: 249; retained as source values and separately flagged, excluded from primary response count and mean per survey timing policy.
- Handle time: 11,183 eligible / 11,750 tickets; mean 1,646.85 min, median 29.00, p75 1,550.00, p90 4,496.80.
- First-response SLA: 11,750 eligible; 1,064 breached, rate 9.06%; 0 not evaluable.
- Transfers: 1,215 total across 11,750 valid ticket counts; 1,097 tickets with at least one transfer (9.34%).

## Data quality and limitations

- Stage 1 tickets without effective roster context: 567, retained in metrics. Breakdown by status: open=335, pending=232. These lack a usable resolution-time assignment context; agent ID summaries remain available where agent_id exists.
- Stage 1 ticket-linked signup anomaly flags: 27; product pre-launch flags: 19; degraded text heuristic flags: 21; reconciliation candidate flags: 0.
- Stage 1 source findings include 206 orders before customer signup and 19 pre-launch ticket matches. These are preserved and are not treated as agent failures.
- Text quality detection under-flags relative to the email thread's approximate forty IVR-junk estimate; text findings require careful interpretation.
- SLA rates exclude tickets without usable creation/first-response timestamps and channels without a configured target. Missing response is not treated as a breach.
- Handle-time eligibility requires a completed ticket, both first response and resolution timestamps, and a non-negative duration. Outliers are retained.
- CSAT response rate is valid 1–5 scores divided by completed tickets. No threshold-based CSAT percentage is defined.
- Percentiles use linear interpolation over the eligible observations. No inference, ranking, Tier comparison, or case-mix adjustment is performed.
