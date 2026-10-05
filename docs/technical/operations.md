# Operations Guide

## Service contract

The service is a stateless Streamlit dashboard. It serves a precomputed, reduced bundle mounted read-only at `/app/runtime-data`; it does not run the analytical pipeline, read source inputs, or call an AI provider at startup. The image and matching data release must be promoted as a pair. The dashboard has no built-in authentication; the deployment owner must supply an approved access boundary and TLS.

## Health and monitoring

Run `python -m app.healthcheck` in the runtime environment or inspect Docker health. The JSON status is `healthy`, `degraded`, or `unhealthy`:

- `healthy`: bundle integrity/schema and Streamlit health endpoint pass; optional AI and Stage 7 evidence are present.
- `degraded`: deterministic bundle/process is valid, while optional AI or Stage 7 evidence is absent. Current AI absence is expected and does not prevent dashboard use.
- `unhealthy`: required data is missing/corrupt, bundle integrity or schema validation fails, or the Streamlit health endpoint is unavailable.

Docker exits health-check successfully for healthy/degraded and fails for unhealthy. This is a process/container signal, not a monitoring service. A host operator should scrape Docker health and container state, collect stdout/stderr logs, alert on `unhealthy`, restart loops, and sustained service unavailability, and retain release ID/image digest with each event. Treat `degraded` as a warning requiring review, not an outage, unless the release owner explicitly requires optional AI/Stage 7 evidence.

Application logs are single-line structured records to stdout/stderr. Use `docker logs --since 30m <container>` for initial triage. Logs intentionally omit source rows, ticket text, agent notes, identifiers, credentials, and authorization headers. No metrics backend, centralized log store, paging integration, or scheduled job is included by this repository; the deployment owner must configure and test those integrations.

## Controlled data refresh

Run refresh from a trusted build workspace containing the raw source pack and locked dependencies. Keep raw/interim data outside the serving container. For example:

```powershell
python -m uv run python scripts/refresh_release.py --release-id 2026-10-05-r1
```

The refresh sequence runs Stages 1–6, requires their reports and data checks to pass, runs Stage 7 and checks its saved audit, creates a reduced bundle in an isolated candidate directory, validates schemas and hashes, then installs it at `data/releases/<release-id>`. It never activates or restarts the service. A failed gate exits non-zero and must not be treated as a releasable bundle. Release IDs are immutable; use a new ID for a new refresh. `data/candidates/` and `data/releases/` are ignored by Git.

Archive the release directory in access-controlled artifact storage with its image digest/tag, source snapshot hash, source-file hashes, pipeline revision, configuration hash, and validation reports. Raw/interim datasets can contain sensitive ticket content and require stricter access than the reduced bundle.

## Activate and verify

Use a unique image tag/digest and immutable bundle release. First start a candidate container on a non-production port with the bundle mounted read-only. Confirm Docker health is healthy/degraded, inspect health JSON, and load the page. Then apply the deployment platform's approved rollout process. Record image digest, release ID, timestamp, operator, and verification. Do not overwrite an existing release directory or edit a release in place.

```powershell
docker run -d --name vireo-candidate `
  -p 8502:8501 `
  --mount "type=bind,source=$((Resolve-Path data/releases/2026-10-05-r1).Path),target=/app/runtime-data,readonly" `
  vireo-support-intelligence:<immutable-tag>
docker inspect --format '{{.State.Health.Status}}' vireo-candidate
docker logs vireo-candidate
```

The example is a local smoke check, not a production deployment configuration. Restrict the published port to a trusted interface/network in the actual environment.

## Rollback and recovery

Retain the last known-good immutable image digest and matching bundle. If rollout fails, route traffic back to the old instance or redeploy that image/bundle pair using the platform's rollback mechanism; verify health and page access. Do not pair an old image with an arbitrary new bundle. Preserve failed-release logs and identifiers for diagnosis. For a corrupt/missing bundle, quarantine it, rebuild from trusted source inputs, pass all refresh gates, and publish a new release ID. For a bad source refresh, keep the previous active release and investigate upstream before retrying.

No database migration or mutable application state needs restoration. This repository does not automate traffic switching, backups, monitoring, alerting, secrets distribution, or host recovery; those remain deployment-owner responsibilities.

## Refresh evidence and lineage

`deployment_manifest.json` records application version, source-file hashes and sizes, aggregate source snapshot hash, pipeline revision/dirty state, configuration SHA-256, reporting period, creation timestamp, per-output hashes/sizes/schema, and row counts. Runtime health rechecks bundle files against this manifest. Keep the manifest with the bundle and record the immutable release ID in deployment logs. A dirty pipeline revision can be used for local evaluation but requires review before an approved release.
