# Data Dictionary

Source definitions come from `data/raw/README.txt`; CSV fields are initially loaded as strings. Observed row counts from this pack are documented in `data_forensics.md`.

## Datasets and keys

| Dataset | Grain | Key / relationship |
|---|---|---|
| tickets | One row per support ticket | `ticket_id`; `customer_id` to customers; nullable `order_id` to orders; `product_sku` to products; `agent_id` to effective-dated roster rows |
| agents | One row per assignment interval | `agent_id` is deliberately non-unique; assignment keyed by agent ID plus `from_date`/`to_date` interval |
| customers | One row per customer | `customer_id` |
| orders | One row per order | `order_id`; `customer_id` to customers and `sku` to products |
| products | One row per SKU | `sku` |

`support-policy.pdf`, `email-thread.txt`, and `README.txt` are source references, not tabular dimensions.

## Important source columns

- Tickets retain `status`, `channel`, `category`, `priority`, `assigned_team`, resolving `agent_id`, `transfers`, `csat_score`, refund/replacement fields, customer text, and `source_system`.
- Ticket handle-time inputs are `first_response_at` and `resolved_at`. Blank CSAT remains blank; it is not converted to zero.
- Agents retain `team`, `tier`, `site`, `shift`, and effective dates. Resolve roster data by `agent_id` and time, never display name.
- Orders retain `customer_id`, `sku`, date, quantity, value, and lot. If ticket `order_id` is blank, `customer_id + product_sku` is the documented fallback; ambiguous candidate sets remain unresolved.
- Customer `signup_date` and product `launch_date` are preserved. Signup/order and ticket/prelaunch anomalies are flagged, never corrected or deleted.

## Canonical normalized fields

The pipeline writes `normalized_{tickets,agents,customers,orders,products}.parquet` in `data/interim/`. Ticket canonical rows retain `created_at_raw`, `first_response_at_raw`, and `resolved_at_raw`, and normalized timestamp fields in UTC ISO format. Naive helpdesk timestamps are interpreted as IST; legacy reconstructed `resolved_at` values are interpreted as UTC. `timestamp_normalization_reason` records the applicable source rule.

Ticket outputs include effective roster attributes prefixed `agent_`, `agent_assignment_flag`, `text_quality_flag` and reason, `signup_anomaly_flag`, `product_prelaunch_anomaly_flag`, `order_match_flag`, and cross-source `reconciliation_flag` and reason. No flagged rows are removed. `normalization_changes.json` records text-normalization edits where present; raw source files are never modified.
