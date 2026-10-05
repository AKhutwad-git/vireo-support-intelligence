# Final Release Acceptance Record

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
