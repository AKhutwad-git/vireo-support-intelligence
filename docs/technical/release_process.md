# Release Process

## Release gates

Do not activate until all gates are evidenced for the exact revision and matching data release:

1. Locked dependency setup and full test suite pass.
2. Stages 1–6 finish with passing required reports and non-empty source quality checks.
3. Stage 7 passes and confirms source ticket-grain integrity; retain its limitations in the release notes.
4. `scripts/refresh_release.py --release-id <new-id>` succeeds and writes a valid immutable reduced bundle.
5. Docker image builds from the same source revision. A disposable container with that image and bundle reports healthy/degraded, serves the dashboard, and passes the browser smoke check.
6. Remote CI for the exact commit succeeds; owner security, network, monitoring, and access-control checks are approved.
7. Release owner records explicit image digest/tag, bundle release ID, revision/config/source hashes, evidence, and approval.

Any failed gate blocks activation. A green local test or old CI run does not prove the current revision passes CI.

## Build candidate

Run the controlled refresh command from the project root. Release IDs are unique and immutable. Verify the command's JSON `status`, `release_path`, `application_version`, agent count, and Stage 7 verdict. Review `deployment_manifest.json` and archive the bundle with the image. Never place raw/interim data in the image or serving mount.

## Rollout

Build and tag an immutable image; do not reuse a mutable `latest` reference for release records. Start a candidate with the read-only bundle on an isolated port/instance. Verify container health, health JSON, dashboard load, representative filter/export behavior, and logs. Roll traffic according to the deployment platform. Record the production verification and retain the previous known-good image/bundle pair.

## Rollback

If candidate checks fail or production health degrades, use the platform to return traffic to the previous known-good instance or redeploy the previous exact image/bundle pair. Verify both health and page load. Preserve the failed release and diagnostic logs; do not mutate it. Create a new release ID after remediation and repeat all gates.

## Stage 7 analytical caveat

The current evaluation verdict is **VALIDATED WITH MATERIAL LIMITATIONS**. Approximate intervals, absence of agent-quality ground truth, no genuine out-of-time validation, incomplete clustered case-mix uncertainty, 567 tickets without effective roster context, valid handle-time outliers, and resolver-based SLA attribution must remain visible in decision use. Stage 5 real-provider quality/cost is not established. No release may describe the result as causal proof or guaranteed savings.
