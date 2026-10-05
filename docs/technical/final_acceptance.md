# Production Acceptance Record

This record is for a specific source revision, image digest, bundle release ID, and host. Fill evidence rather than inferring acceptance from repository implementation.

## Evidence record

| Gate | Result | Evidence / revision |
| --- | --- | --- |
| Full test suite | PASS (local working tree) | 119 passed, 1 skipped; 2026-10-05 |
| Stages 1–6 pipeline | PASS | Controlled refresh `stage10-20261005-local1` |
| Stage 7 evaluation and limitations review | PASS with material limitations | Controlled refresh; verdict unchanged |
| Refresh gates and immutable bundle manifest | PASS | Release `stage10-20261005-local1`; 44 agents |
| Exact-revision remote CI | NOT VERIFIED | Working tree is uncommitted; GitHub Actions API query returned 404 |
| Docker build | PASS (local) | `vireo-support-intelligence:0.1.0`, image ID `61601566401d` |
| Candidate container health and dashboard load | PASS (local simulation) | Docker healthy; semantic degraded for AI absence; 44 agents; health URL HTTP 200; rendered dashboard observed |
| Browser filter/export check | NOT VERIFIED | Dashboard loaded; browser-level filter combinations and downloaded CSV persistence not independently checked |
| Corrupt bundle detection and known-good preservation | PASS (local simulation) | Health returned unhealthy on manifest hash mismatch; immutable good bundle remained valid |
| Rollback smoke | PASS (local simulation) | Saved Stage 9 image + prior bundle returned Docker healthy, health URL HTTP 200 |
| Host authentication, TLS, network and security review | NOT VERIFIED | Must be evidenced by the deployment owner |
| Monitoring and alert delivery | NOT VERIFIED | Procedures documented; no monitoring/paging platform configured here |
| Rollback/restore drill | PARTIAL | Local image/bundle smoke only; no target-host traffic rollback or backup restore |
| Release owner approval | PENDING | No deployment owner approval recorded |

## Acceptance rule

Production acceptance requires every gate to pass for the same source revision and image/bundle pair, plus the host-owner checks and approval. The evidence above documents local Stage 10 simulation only. A local pass cannot substitute for remote CI or target-host security, monitoring, or operational evidence. An expected degraded state caused only by absent optional AI/Stage 7 bundle evidence may be accepted only when the release owner documents that decision; deterministic data and process health must pass.

The candidate manifest records base revision `db92ad1facc568cfff5aad537b14b9e3245cee16` with `pipeline_worktree_dirty=true`: the Stage 10 implementation is still uncommitted. Treat this bundle/image as verification artifacts only. After the implementation is reviewed and committed, rerun the gated refresh with a fresh release ID and build/tag the final image from that clean revision before any release approval.

## Known decision-use limitations

Stage 5 model evaluation is unavailable. Stage 7's verdict remains **VALIDATED WITH MATERIAL LIMITATIONS**: intervals are approximate, agent-quality ground truth and genuine out-of-time validation are absent, and clustered case-mix uncertainty is incomplete. 567 tickets lack effective roster context, valid handle-time outliers remain, and SLA attribution uses resolver identity because first-response actor identity is absent. Dashboard results are decision support, not evidence of causality or guaranteed savings.
