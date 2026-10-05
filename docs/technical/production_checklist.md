# Stage 9 Deployment Readiness Checklist

This checklist records implementation and validation separately. Do not mark a deployment host check complete based on local Streamlit tests.

## Build

- [x] Single-container Dockerfile added; Python 3.13 slim, locked runtime requirements, unprivileged user.
- [x] `uv.lock`, hash-checked `requirements.lock`, and dev lock generated.
- [ ] `docker build -t vireo-support-intelligence:0.1.0 .` run successfully on a Docker host. Docker is not installed in the current authoring environment.
- [ ] Image tag and reduced data bundle stored together in the target artifact registry.

## Test

- [x] Full `python -m uv run pytest -q` run from the clean locked environment: 104 passed, 1 skipped.
- [x] Configuration/import/synthetic smoke test implemented as `scripts/validate_install.py`.
- [ ] CI workflow observed passing on the repository's remote.
- [x] Full pipeline and Stage 7 reports refreshed from the current source pack: both PASS.

## Security

- [x] `.gitignore` excludes environment secrets, raw task data, generated interim data, and Streamlit secrets.
- [x] `.dockerignore` excludes data, credentials, tests, and development artifacts; Dockerfile copies only `app/` and `src/`.
- [x] Container runs as non-root; AI key is not required by or passed to the dashboard image.
- [x] Reduced dashboard data package omits ticket-level messages, notes, customer data, and machine-local report paths.
- [x] CORS and XSRF protection remain enabled.
- [ ] Network boundary, TLS termination, and access restriction configured for the actual host.
- [ ] Security review approved for the actual deployment data and host.

## Configuration and data

- [x] Dashboard bundle path, logging level, and optional AI secret behavior documented.
- [x] Bundle packaging validates schemas and agent ID alignment before output.
- [x] Reduced deployment bundle generated from the latest successful pipeline and Stage 7 outputs.
- [ ] Deployment bundle stored read-only at the target.
- [ ] Bundle/image version pairing recorded by deployment owner.

## Health and startup

- [x] Startup data validation and health states (`healthy`, `degraded`, `unhealthy`) implemented.
- [x] Health check verifies required dashboard schemas/data and Streamlit process endpoint; no AI or full pipeline call.
- [x] Clean-environment Streamlit start, HTTP 200, and health state `degraded` with valid data/no AI verified locally.
- [ ] Health check successfully executed inside the built container with the target bundle.
- [ ] App startup and page load observed in the built container/target runtime.

## Rollback and known limitations

- [x] Basic image/bundle rollback and rebuild recovery steps documented.
- [ ] Prior known-good image and bundle retained in deployment artifact storage.
- [x] Stage 5 and Stage 7 analytical limitations documented and preserved.

## Stage boundary

Stage 9 does not provide production monitoring, scheduled refresh, alerting, incident management, cloud infrastructure, or production acceptance. Those remain Stage 10 items.
