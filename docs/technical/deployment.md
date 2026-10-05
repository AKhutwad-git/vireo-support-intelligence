# Deployment Architecture and Operations

## Deployment model

One Streamlit container serves the client-facing dashboard on TCP port 8501. There is no API service, database, job scheduler, or model server. Python 3.13 slim is the container runtime; the project source declares Python 3.10+ support, while the container and CI use Python 3.13.

The container uses locked runtime dependencies from `requirements.lock`, runs as the unprivileged `vireo` user, and starts Streamlit directly in headless mode. Streamlit's CORS and XSRF protections remain enabled. The app version is available as `vireo.__version__` and in the sidebar. Container image tag and the matching data bundle should be versioned together.

## Data lifecycle and safety

Deployment uses precomputed data (Option A). The deterministic pipeline and Stage 7 evaluation run outside the serving container. After both pass, use the controlled refresh flow to build and immutably install a candidate release:

```bash
python -m uv run python scripts/refresh_release.py --release-id <new-unique-release-id>
```

The refresh gate requires passing Stages 1–6 reports and Stage 7 evaluation before packaging. The packager validates app schema/agent joins and writes four aggregate Parquet tables (`training_priority`, `agent_comparison`, `agent_economics`, `agent_metrics`), summary-only Stage 2/4 JSON, an allowlisted Stage 5 status summary, and optional aggregate AI diagnostics/Stage 7 report. `deployment_manifest.json` records file sizes and SHA-256 hashes plus source snapshot/file hashes, pipeline revision/dirty state, config hash, reporting period, and creation time. Raw ticket-level metrics, normalized tickets, customer/order data, source documents, ticket messages, and agent notes are excluded. The flow validates and installs an immutable release but does not activate the serving app.

Raw files in `data/raw/` are source/build-time inputs, not runtime files. Full `data/interim/` is generated and can contain customer-level message and agent-note fields; never mount it into the serving container. Mount only the reduced bundle at `/app/runtime-data` as read-only. The app requires four Parquet files plus Stage 2 and Stage 4 dashboard summaries. Stage 7 and AI files are optional; AI diagnostics are unavailable in the current run.

The bundle is an operationally sensitive internal-agent output. Store it in an access-controlled artifact location even though customer messages and notes are excluded. The dashboard itself has no authentication; limit network access to an approved internal network/reverse proxy and provide TLS at that boundary.

## Dependencies and build

- Local/project supported Python: 3.10 or later (declared in `pyproject.toml`). The verified deployment target is Python 3.13.
- `uv.lock`: locked cross-platform package resolution, including the `dev` extra.
- `requirements.lock`: production runtime requirements exported with hashes for pip's `--require-hashes`.
- `requirements-dev.lock`: pip-compatible lock export including development dependencies.
- `Dockerfile`: single image; does not copy `data/`, secrets, tests, or docs.

Build with:

```bash
docker build -t vireo-support-intelligence:0.1.0 .
```

## Configuration and secrets

| Variable | Required | Meaning |
|---|---:|---|
| `VIREO_INTERIM_DIR` | Yes for container | Read-only reduced dashboard bundle. The image sets `/app/runtime-data`; local default is project `data/interim`. Relative local values resolve against the project root. |
| `VIREO_LOG_LEVEL` | No | Python log threshold; default `INFO`. |
| `VIREO_AI_API_KEY` | No | Optional Stage 5 pipeline credential only. It is not required or used by the dashboard container. |

`.env.example` is reference-only. The application does not load `.env`. Use a process environment or secret manager for the optional AI key; do not pass it to the dashboard container. The image build has no secret build argument and does not copy `.env` files. The app logs whether the optional key is present but never its value.

## Startup and health

The process uses `/app` as its working directory; data/resource paths are resolved from the module path and `VIREO_INTERIM_DIR`, not the invoking shell's working directory. Startup reads/validates required Parquet schemas, checks that the comparison table has full-period rows, checks agent ID alignment, and loads the Stage 2/4 summaries. It does not run the pipeline or call a model.

The health command validates the dashboard data contract and bundle hashes and checks Streamlit's `/_stcore/health` endpoint. It does not call AI or rerun analysis:

```bash
python -m app.healthcheck
```

It returns JSON with `healthy`, `degraded`, or `unhealthy`. Missing/corrupt deterministic output is unhealthy. Missing AI evidence or Stage 7 report is degraded and leaves the deterministic dashboard usable. The container's Docker health check exits successfully for healthy/degraded, and unsuccessfully for unhealthy.

## Logging

Structured single-line Python logs default to INFO. They record app version, optional/offline AI mode, validated agent count, health state, and unexpected errors. No source rows, ticket text, agent notes, IDs, API key values/presence, or authorization headers are logged. Streamlit/Uvicorn emits its normal server startup and request logs.

## Run

```bash
docker run -d --name vireo-support-intelligence --restart unless-stopped \
  -p 8501:8501 \
  --mount type=bind,source="$(pwd)/data/releases/<release-id>",target=/app/runtime-data,readonly \
  vireo-support-intelligence:0.1.0
```

Verify the page at `http://localhost:8501` and check:

```bash
docker inspect --format '{{.State.Health.Status}}' vireo-support-intelligence
docker logs vireo-support-intelligence
```

## CI

`.github/workflows/tests.yml` installs the locked dev set, checks imports, runs the deterministic synthetic decision smoke and relevant unit/deployment contract tests, then builds the image. The raw customer source pack and generated deployment bundle are intentionally not committed; data-dependent integration tests skip when those artifacts are unavailable. CI does not call the real provider or run the full source-pack pipeline.

## Rollback and recovery

Retain a known-good immutable image digest/tag and its matching immutable reduced bundle in the deployment artifact store. To roll back: route traffic to the prior instance or redeploy the prior exact image/bundle pair. The app is stateless; no database migration or user state restoration is needed. For missing or corrupt outputs, quarantine that release, rebuild from a fresh successful deterministic pipeline and Stage 7 report through `scripts/refresh_release.py` using a new release ID, and promote the bundle/image pair together. See [operations](operations.md), [release process](release_process.md), and [incident response](incident_response.md).

## Security and analytical limitations

No authentication is built into the app. Use a trusted network boundary and TLS termination appropriate to the actual host. This is not a security certification. Stage 5 real-model quality/cost is unavailable; Stage 7 remains validated with material limitations. Stage 3 uncertainty is approximate and independent-ticket based; no real-world decision ground truth, genuine out-of-time validation, or full clustered case-mix uncertainty exists. 567 tickets lack effective roster context; valid handle-time outliers remain; SLA is associated with resolver identity because first-response actor identity is absent. The dashboard does not establish agent causality or guaranteed savings.

Monitoring backends, scheduled refresh, alert delivery, access-management integration, target-host security review, and production acceptance require deployment-owner configuration. The repository now defines operational procedures and gated refresh tooling; those documents do not imply that external services or host acceptance have been completed. See [the Stage 10 checklist](production_checklist.md) and [acceptance record](final_acceptance.md).
