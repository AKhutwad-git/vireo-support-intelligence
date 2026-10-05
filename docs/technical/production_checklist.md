# Vireo Support Intelligence — Stage 10 Operations Checklist

This checklist separates repository evidence from host-owner acceptance. A checked local test does not imply that a production host, security boundary, or monitoring service exists.

## Refresh and release

- [x] Refresh script gates packaging on Stages 1–6 reports, Stage 7, and unique Stage 1 ticket grain.
- [x] Candidate bundle is built in an isolated directory, hashed, schema-validated, and installed under an immutable release ID.
- [x] Existing bundle destinations are never overwritten; failed candidate validation does not promote.
- [x] Runtime health verifies bundle inventory, sizes, SHA-256 hashes, version, and dashboard schemas.
- [x] Run `scripts/refresh_release.py` successfully against the current source pack: release `stage10-20261005-local1`, 44 agents, Stages 1–6 PASS, Stage 7 PASS.
- [x] Complete the local test suite (119 passed, 1 skipped), pipeline, Stage 7, image build, candidate container health, HTTP page health, and rendered dashboard check for this working tree.
- [ ] Observe a successful remote CI run for the exact revision to be released. This working tree is uncommitted; the GitHub Actions API returned 404 for the prior `db92ad1` run query, so remote evidence is unavailable here.
- [ ] Independently verify browser filter combinations and downloaded CSV persistence for the release candidate.
- [ ] Release owner records approval and activates a version-paired image and bundle.

## Runtime and recovery

- [x] Operational, incident response, release, and acceptance procedures are documented.
- [x] Health states, log signals, degraded AI behavior, refresh gates, rollback, and recovery are defined.
- [ ] Host monitoring/alert delivery is configured and exercised by the deployment owner.
- [ ] Actual deployment host has approved authentication, TLS, network restriction, secrets, and access controls.
- [ ] Host owner completes backup/restore and rollback drill and records evidence.
- [ ] Security review and production acceptance are signed by the responsible owner.

## Analytical/product limitations

- [x] Stage 5 provider/model quality and cost evaluation is unavailable; AI remains optional and does not control numeric metrics.
- [x] Stage 7 is validated with material limitations: approximate independent-ticket intervals, no quality ground truth, no genuine out-of-time validation, and no complete clustered case-mix uncertainty.
- [x] 567 tickets lack effective roster context; valid handle-time outliers remain; SLA is associated with resolver identity because first-response actor identity is absent.
- [x] Dashboard outputs are decision support and do not establish agent causality or guaranteed savings.

## Current acceptance status

Repository procedures and gated release tooling are implemented. The new candidate image is `vireo-support-intelligence:0.1.0` (image ID `61601566401d`) and release bundle is `stage10-20261005-local1`. Runtime Docker health was `healthy`; semantic health was `degraded` only because AI diagnostics were unavailable (deterministic data valid, 44 agents, 6 outputs validated, process alive). The page and `/_stcore/health` returned successfully in the isolated candidate. Corrupt-manifest simulation returned `unhealthy` with a bundle integrity error while the good immutable release remained valid. A separate rollback smoke using the saved Stage 9 image and its prior bundle returned healthy Docker status, degraded semantic health for expected AI absence, and HTTP 200. The pre-existing service on port 8501 was left unchanged.

Production acceptance remains incomplete until exact-revision remote CI, browser filter/export verification, target-host security and monitoring, owner activation, and signed acceptance are evidenced. The candidate container was a local acceptance simulation, not production traffic.
