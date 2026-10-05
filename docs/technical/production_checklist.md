# Production and Submission Checklist

This checklist distinguishes local release evidence from target-host acceptance. A successful local container run does not imply production deployment approval.

## Current release evidence

- [x] Source commit `4b16ca55fa57a19214b6e3b1164b9ef24f4e000c` is on `origin/main` and the release build used a clean worktree.
- [x] Stage 1–6 pipeline and Stage 7 passed for release `final-20261006-04`; Stage 7 verdict remains **VALIDATED WITH MATERIAL LIMITATIONS**.
- [x] Immutable bundle `final-20261006-04` validates: version `0.1.0`, 44 agents, hashes/schema/joins pass, `pipeline_worktree_dirty=false`.
- [x] Full local suite: 119 passed, 1 skipped, 0 failed.
- [x] Image `vireo-support-intelligence:0.1.0-final-20261006-04` built locally from the release source commit; image digest is in `docs/submission/release-record.md`.
- [x] Candidate `vireo-final-20261006-04` on port 8504 ran as UID/GID 999 `vireo`, with read-only bundle mount and Docker health `healthy`.
- [x] Semantic health: deterministic data valid; 44 agents; six outputs validated; process alive; AI unavailable/degraded as expected.
- [x] `/_stcore/health` returned HTTP 200; rendered dashboard showed 0 candidates and 44 monitor agents.
- [x] Stage 7 generated report no longer claims repository documentation/dashboard/deployment artifacts are absent.
- [x] Exact-SHA GitHub CI: `python-tests` completed successfully for `4b16ca55fa57a19214b6e3b1164b9ef24f4e000c`.
- [ ] Browser filter combinations and CSV download persistence independently verified on this final candidate.

## External acceptance gates

- [ ] Target-host deployment and target-host security review approved.
- [ ] Authentication/access boundary, TLS, network restriction, and secrets handling verified on the actual host.
- [ ] Central monitoring, log collection, and paging/alert delivery configured and tested.
- [ ] Target-host rollback/restore drill and release-owner approval recorded.
- [ ] Original client submission form obtained; the repository file is only an internal status note.

## Limitations that remain

- [x] Stage 5 real-model quality and cost evaluation are unavailable; no provider requests or real predictions occurred in this run.
- [x] Stage 7 limitations remain: approximate intervals; no ground-truth personnel-quality measurement; no genuine out-of-time validation; incomplete clustered case-mix uncertainty.
- [x] 567 tickets lack effective roster context; valid handle-time outliers remain; SLA is resolver-associated because verified first-responder identity is unavailable.
- [x] Outputs are decision support, not causal personnel conclusions or guaranteed savings.

See [final acceptance](final_acceptance.md), [release record](../submission/release-record.md), [operations](operations.md), and [release process](release_process.md) for evidence and procedures.
