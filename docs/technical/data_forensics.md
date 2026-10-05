# Data Forensics

Generated from the current raw task pack. No business conclusions are calculated.

## Source inventory

| File | Present |
|---|---:|
| `tickets.csv` | yes |
| `agents.csv` | yes |
| `customers.csv` | yes |
| `orders.csv` | yes |
| `products.csv` | yes |
| `support-policy.pdf` | yes |
| `email-thread.txt` | yes |
| `README.txt` | yes |

## Observed tables

| Dataset | Rows | Columns |
|---|---:|---:|
| `tickets` | 11750 | 21 |
| `agents` | 44 | 8 |
| `customers` | 9500 | 6 |
| `orders` | 15500 | 8 |
| `products` | 14 | 7 |

## Null rates

| Dataset | Column | Nulls | Null rate |
|---|---|---:|---:|
| tickets | resolved_at | 567 | 4.83% |
| tickets | order_id | 4107 | 34.95% |
| tickets | csat_score | 6554 | 55.78% |
| tickets | refund_amount_inr | 9881 | 84.09% |
| tickets | refund_reason_code | 9881 | 84.09% |
| agents | to_date | 44 | 100.00% |

## Checks

| Status | Check | Dataset | Finding |
|---|---|---|---|
| PASS | source_file_presence | — | All expected source files found |
| PASS | required_columns | tickets | Required columns present |
| PASS | critical_identifier_nulls | tickets | 0 rows have a null/blank ticket_id |
| PASS | duplicate_key | tickets | 0 duplicate ticket_id values |
| PASS | date_parse | tickets | 0 invalid values in created_at |
| PASS | date_parse | tickets | 0 invalid values in first_response_at |
| PASS | date_parse | tickets | 0 invalid values in resolved_at |
| PASS | row_count | tickets | Observed 11750 rows |
| PASS | required_columns | agents | Required columns present |
| PASS | date_parse | agents | 0 invalid values in from_date |
| PASS | date_parse | agents | 0 invalid values in to_date |
| PASS | row_count | agents | Observed 44 rows |
| PASS | required_columns | customers | Required columns present |
| PASS | critical_identifier_nulls | customers | 0 rows have a null/blank customer_id |
| PASS | duplicate_key | customers | 0 duplicate customer_id values |
| PASS | date_parse | customers | 0 invalid values in signup_date |
| PASS | row_count | customers | Observed 9500 rows |
| PASS | required_columns | orders | Required columns present |
| PASS | critical_identifier_nulls | orders | 0 rows have a null/blank order_id |
| PASS | duplicate_key | orders | 0 duplicate order_id values |
| PASS | date_parse | orders | 0 invalid values in order_date |
| PASS | row_count | orders | Observed 15500 rows |
| PASS | required_columns | products | Required columns present |
| PASS | critical_identifier_nulls | products | 0 rows have a null/blank sku |
| PASS | duplicate_key | products | 0 duplicate sku values |
| PASS | date_parse | products | 0 invalid values in launch_date |
| PASS | row_count | products | Observed 14 rows |

## README source definitions

`README.txt` was read (2635 characters). Its definitions remain authoritative; the file format is not assumed or auto-parsed. Populate `datasets` and `relationships` in configuration from those definitions before treating key or relationship checks as complete.

## Missingness and duplicates

Null rates and duplicate key findings are recorded in the generated schemas and checks. Agents intentionally have a non-unique agent_id because README defines one row per effective-dated assignment.

## Stage 1 findings

- Orders dated before customer signup: 206 order rows (source-known anomaly; retained).
- Ticket rows linked to an order dated before customer signup: 27.
- Product pre-launch ticket matches: 19.
- Degraded customer messages under deterministic heuristic: 21; email thread estimates roughly forty IVR-junk records, so unflagged candidate review remains unresolved.
- Cross-source duplicate candidate rows on matching customer, SKU, and source creation timestamp: 0.
- Tickets without effective roster match: 567 (includes open/unassigned tickets).
- Negative first-response-to-resolution intervals after UTC normalization: 0; raw source values are preserved and these are flagged for review, never shifted to force non-negative durations.

## Joins and source relevance

Relationships are counted in `data_quality_report.json`; nullable ticket order_id values are excluded from the direct order lookup check. Customer plus product SKU is used only as a unique fallback; ambiguous matches are left unresolved. Roster assignments are selected by agent_id and effective dates. No join expands ticket rows.
The policy PDF is inventoried but not text-extracted in this run; its economics are not treated as system constants. README/email text is available for provenance and semantics.

## Audit classification

| Requirement | Status | Basis |
|---|---|---|
| Source inventory and missing dependency reporting | PASS | All required task pack files are inventoried; missing files fail the pipeline. |
| Contract/schema and key validation | PASS | README columns and primary identifiers are validated; roster agent_id is intentionally non-unique. |
| Source-aware timestamps and effective roster | PARTIAL | Implemented, but legacy created/first-response provenance is not documented precisely; only legacy resolved_at is treated as UTC. |
| Anomaly, text-quality, reconciliation flags | PARTIAL | Signup/product flags work; text heuristic flags 21 while email context estimates ~40, and exact-timestamp duplicate matching may miss near-time re-imports. |
| Relationship and row-count-safe joins | PARTIAL | Temporal roster assignment is used and no expanding join is applied; relationship findings are diagnostic, and ambiguous order links remain unresolved. |
| Reproducible canonical outputs and forensic reporting | PASS | Parquet tables and generated report written when validation passes. |
| Business KPI/ranking or Stage 2 modeling | PASS | Not implemented. |

## Canonical outputs

- `tickets`: 11750 rows at `C:\Users\admin\Desktop\NewProjects\vireo-support-intelligence\data\interim\normalized_tickets.parquet`
- `agents`: 44 rows at `C:\Users\admin\Desktop\NewProjects\vireo-support-intelligence\data\interim\normalized_agents.parquet`
- `customers`: 9500 rows at `C:\Users\admin\Desktop\NewProjects\vireo-support-intelligence\data\interim\normalized_customers.parquet`
- `orders`: 15500 rows at `C:\Users\admin\Desktop\NewProjects\vireo-support-intelligence\data\interim\normalized_orders.parquet`
- `products`: 14 rows at `C:\Users\admin\Desktop\NewProjects\vireo-support-intelligence\data\interim\normalized_products.parquet`
