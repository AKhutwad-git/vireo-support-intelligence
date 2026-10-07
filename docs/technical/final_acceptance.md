# Historical Release Acceptance Record — `final-20261006-04`

This record describes the historical `final-20261006-04` image/bundle pair and its stated source SHA. It does not describe the newer candidate currently promoted on ports 8501 and 8505. The candidate was built from a dirty working tree based on `47d3b1c`; final clean-source acceptance is still pending.

This record describes the locally verified release source, bundle, and image. It is not production approval. The tracked evidence record may be committed after the release build; its release source SHA below is the SHA recorded in the bundle manifest and used to build the image.

## Release identity

- Release ID: `final-20261006-04`
- Application version: `0.1.0`
- Release source commit: `4b16ca55fa57a19214b6e3b1164b9ef24f4e000c`
- Bundle pipeline worktree dirty: `false`
- Bundle validation: `PASS` (manifest inventory, hashes, schemas, joins; 44 agents)
- Stage 1–6 pipeline: `PASS`
- Stage 7: `PASS`; verdict **VALIDATED WITH MATERIAL LIMITATIONS**
- Stage 5/AI: unavailable; zero real provider requests and zero real predictions in this run

## Verification evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Full test suite | PASS | 119 passed, 1 skipped, 0 failed; 2026-10-06. Run against the source changes committed as the release source revision. |
| Exact-source pipeline and Stage 7 | PASS | `scripts/refresh_release.py --release-id final-20261006-04`; clean source revision in manifest |
| Bundle schema, joins, inventory and hashes | PASS | `data/releases/final-20261006-04`; 9 inventoried files; 44 agents |
| Image build | PASS (local) | `vireo-support-intelligence:0.1.0-final-20261006-04`; image ID/config digest and local image digest recorded in [`release-record.md`](../submission/release-record.md) |
| Candidate runtime | PASS (local) | Container `vireo-final-20261006-04`; port 8504; UID/GID 999 `vireo`; Docker health `healthy`; release mount read-only |
| Runtime semantic health | DEGRADED as expected | Deterministic data valid; 44 agents; six outputs validated; AI unavailable; process alive; no errors |
| HTTP and rendered dashboard | PASS (local) | `/_stcore/health` HTTP 200; dashboard rendered in browser with 0 training candidates and 44 monitored agents |
| Browser filter combinations / CSV persistence | NOT VERIFIED | Not exercised in this final-release run |
| Exact-SHA remote CI | PASS | `python-tests` completed successfully for `4b16ca55fa57a19214b6e3b1164b9ef24f4e000c` |
| Target-host deployment and security acceptance | NOT VERIFIED | Local Docker test only; no target-host evidence or owner approval |
| Central monitoring and paging | NOT CONFIGURED | Operating contract documented; no external integration verified |

## Acceptance interpretation

**Local release acceptance: verified with material limitations.** The repository release-acceptance gate returned `accepted=true` with tests, pipeline, Stage 7, bundle, image build, container startup, and exact-SHA CI marked PASS. This does not establish target-host deployment or approval. Browser filter/export persistence also remains unverified.

**Target-host production deployment: not verified.** Local validation does not establish target-host security, external monitoring, or production approval. Keep those items open until their specific evidence exists.

## Analytical limitations

Stage 5 real-model quality and cost evaluation are unavailable. Stage 7 remains **VALIDATED WITH MATERIAL LIMITATIONS**: uncertainty intervals are approximate; agent-quality ground truth and genuine out-of-time validation are absent; clustered case-mix uncertainty is incomplete; 567 tickets lack effective roster context; valid handle-time outliers are retained; and SLA is resolver-associated because verified first-responder identity is unavailable. AI does not drive deterministic decisions. The results do not establish agent causality or guaranteed savings.

## Current candidate verification — 2026-10-07

This is a local candidate check, not a replacement immutable release record or target-host approval.

| Gate | Result | Evidence |
| --- | --- | --- |
| Candidate image | PASS | Tag `vireo-support-intelligence:0.1.0-candidate-20261007`; image ID `sha256:49345b6b1b52caf51ca95d177fb9a0f23babe7c647fe406e812c711c575233ff`. The image's `app/streamlit_app.py` SHA-256 matches the current working-tree file. |
| Promoted application and preview | PASS | Containers `vireo-support-intelligence` on 8501 and `vireo-support-intelligence-candidate` on 8505 use the same image ID and the same read-only `data/deployment` bind mount. The 8501 restart policy is `unless-stopped`; 8505 has no restart policy. |
| Bundle | PASS | `data/deployment/deployment_manifest.json` reports version `0.1.0`, excludes raw source data, and inventories product SKU, product family, order channel, lot, and agent-product aggregates. |
| Container and HTTP health | PASS | Both containers report Docker `healthy`; `http://localhost:8501/_stcore/health` returned HTTP 200. Application semantic health is `degraded` because optional AI diagnostics are unavailable; deterministic data is valid and the process is alive. |
| Browser | PASS | 8501 showed Overview, Agents, Agent Detail, Product & Orders, and Methodology / Trust. Product/order aggregates rendered. Agents search returned one result for `A3001`; clearing search restored 44 agents. Overview retained the Bottom 10, Top 5, 9.06%→8.06% goal, ₹41,125 sensitivity, and ₹0/₹400,000 budget decision. |
| Product-family presentation | PARTIAL | The 5-row product-family aggregate is present in the bundle and loaded by `app/dashboard_data.py`, but the Product & Orders page does not render a family-level table. Product family appears only as a column in the SKU/lot/exposure tables. |
| Logs | PASS | Recent 8501 logs show normal Streamlit startup and dashboard loads; no traceback, missing-file, schema, or startup error was present. |
| Full tests | PASS | Current working tree: 135 passed, 1 skipped, 0 failed (`python -m uv run pytest -q`, 2026-10-07). |
| Real AI evaluation | LIMITED | 20 requests; 3 valid predictions, all 3 matched labels; 5 schema failures and 12 HTTP 429. This is not overall model accuracy. Prompt v2 has not been evaluated live; cost is unknown. |
| Git / source identity | BLOCKED | Branch and `origin/main` are at `47d3b1c`, but the working tree has application, analysis, test, and documentation changes not in that commit. The public remote has not received those changes. The running image is a candidate from this dirty source state, not a build tied to a final clean commit. |
| Clean-machine and external acceptance | NOT VERIFIED | No clean checkout reproduction, target-host security/access review, external monitoring, or production approval was evidenced. |

Final source/release consistency requires a committed source state and matching release evidence. Do not cite historical SHA `4b16ca5` or its 119-test result as evidence for this candidate.
