# Vireo Support Intelligence

A deterministic support-operations analysis and decision-support dashboard prepared for the Banao Technologies evaluation. It reports support performance, Tier-safe peer comparisons, observed economics, and evidence-gated training status. It does not infer agent causality or manufacture a bottom-ten list.

## Current result

The current source pack contains 11,750 tickets from January 2025 through June 2026. Stage 6 reports **0 defensible training candidates and 44 monitor agents**. No agent meets the configured interval-based evidence threshold. Three point-estimate-only names from Stage 7 sensitivity (A3015, A3021, A3026) are exploratory and are not recommendations.

Stage 7 passed 12 independent metric reconciliations, eight synthetic decision scenarios, 220 explanation checks, and reproducibility checks. Its readiness verdict is **VALIDATED WITH MATERIAL LIMITATIONS**. The intervals are approximate; there is no agent-quality ground truth, clustered case-mix uncertainty, genuine out-of-time validation, or real Stage 5 model evaluation.

## Requirements

- Python 3.10 or later for local use; Python 3.13 is the validated container runtime.
- uv 0.12.23 for locked dependency installation and updates.
- Docker Engine for container build/run.
- Windows, macOS, or Linux
- Source data files in `data/raw/` (the supplied task pack includes these)

Runtime dependencies are PyArrow, pandas, PyYAML, and Streamlit. Pytest is a development dependency. `uv.lock` records the cross-platform resolution; `requirements.lock` is the hash-checked container runtime export and `requirements-dev.lock` is the pip-compatible development export.

## Install

From the project root:

```bash
python -m venv .venv
```

Activate it:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install the application and test dependencies from the lock:

```bash
python -m pip install uv==0.12.23
python -m uv sync --locked --all-extras
```

## Data placement

Place the source pack files in `data/raw/`. Do not edit source files in place. Required schemas and policy context are documented in `data/raw/README.txt`; the policy PDF and client email are included in the source pack. The analytical pipeline writes generated Parquet/JSON files into `data/interim/` and technical findings into `docs/technical/`.

## Run the deterministic pipeline

```bash
python -m uv run python scripts/run_analysis.py
```

The command rebuilds Stages 1–6, including Stage 5's safe unavailable status when AI is disabled. It does not make an LLM request in the default configuration. Stage 7 runs separately:

```bash
python -m uv run python scripts/run_stage7_evaluation.py
```

## Run the dashboard

Generate the pipeline outputs first, then start Streamlit:

```bash
python -m uv run streamlit run app/streamlit_app.py
```

The dashboard reads generated outputs; it does not rerun analysis on page refresh. It provides Overview, Agents, Agent Detail, and Methodology / Trust pages. The Agents page supports filters and CSV downloads. Stage 7 validation summary JSON is available on Methodology / Trust.

## Test

```bash
python -m uv run pytest -q
```

Tests cover source validation, metric/economics/decision logic, dashboard output schemas and joins, optional AI absence, CSV columns and row counts, and agreement with saved Stage 6 decisions.

## Optional AI configuration

Stage 5 is opt-in and disabled by default in `configs/config.yaml` (`ai.enabled: false`). The client reads the environment variable named by `ai.api_key_env`, currently `VIREO_AI_API_KEY`, when AI is enabled and a model is configured. Copy `.env.example` as a reference only; the code does not load `.env` files automatically. Set the key in your shell environment and explicitly configure the provider/model before running the pipeline. Never commit credentials. There is no live AI action in the dashboard; the dashboard does not need an AI key.

## Architecture

```text
data/raw
  → Stage 1 normalized / validated data
  → Stage 2 deterministic metrics
  → Stage 3 Tier-safe peer and case-mix analysis
  → Stage 4 observed economics
  → Stage 5 optional AI diagnostics
  → Stage 6 deterministic training-priority decisions
  → Stage 7 reconciliation and robustness evaluation
  → app/dashboard_data.py validated presentation views and exports
  → app/streamlit_app.py Streamlit presentation
```

## Deployment (single container)

The container serves the dashboard only. It does not include raw source data or run Stages 1–7 at startup. Deployment uses **Option A: a separately supplied, precomputed reduced dashboard bundle**. Package the outputs after a successful pipeline and Stage 7 run:

```bash
python -m uv run python scripts/package_dashboard_data.py --source-dir data/interim --output-dir data/deployment
```

The packager keeps aggregate agent tables and summary reports, strips ticket-level messages and notes, and excludes machine-local report paths. Store the bundle in a protected deployment artifact location and mount it read-only. Raw source files are build inputs only and are excluded from Git/Docker contexts. The full `data/interim/` can contain ticket-level content; do not mount it into the serving container.

Build and run from the repository root (Bash):

```bash
docker build -t vireo-support-intelligence:0.1.0 .
docker run -d --name vireo-support-intelligence --restart unless-stopped \
  -p 8501:8501 \
  --mount type=bind,source="$(pwd)/data/deployment",target=/app/runtime-data,readonly \
  vireo-support-intelligence:0.1.0
```

PowerShell volume example:

```powershell
docker run -d --name vireo-support-intelligence --restart unless-stopped `
  -p 8501:8501 `
  --mount "type=bind,source=$((Resolve-Path data/deployment).Path),target=/app/runtime-data,readonly" `
  vireo-support-intelligence:0.1.0
```

Open `http://localhost:8501`. The container runs as an unprivileged user. CORS and XSRF protections stay enabled. Check health with:

```bash
docker inspect --format '{{.State.Health.Status}}' vireo-support-intelligence
```

`python -m app.healthcheck` emits JSON status: `healthy`, `degraded`, or `unhealthy`. AI absence yields `degraded` while deterministic functions remain available; Docker treats degraded as a functioning process. Missing/corrupt required outputs or an unavailable Streamlit health endpoint produce `unhealthy`.

### Deployment configuration

| Variable | Secret | Purpose |
|---|---:|---|
| `VIREO_INTERIM_DIR` | No | Dashboard bundle directory. Defaults to project `data/interim`; container sets `/app/runtime-data`. Relative local paths resolve from the project root. |
| `VIREO_LOG_LEVEL` | No | Python log threshold; defaults to `INFO`. |
| `VIREO_AI_API_KEY` | **Yes** | Optional Stage 5 provider key for the analysis pipeline. Not required by the dashboard container and never baked into the image. |

Configure secrets through a deployment platform's secret store or process environment, never the repository, image, or logs. Logs report version, validation/health state, row counts, and errors; they do not contain customer messages, agent notes, authorization headers, or credential values.

### Runtime data and recovery

The image contains application code and locked runtime libraries only. `data/raw/` is needed to rebuild analysis outside the serving container. `data/interim/` is generated and may contain ticket-level content; the container receives only the reduced `data/deployment/` bundle. Keep versioned copies of the image tag and matching bundle. To roll back, stop/remove the current container, restore the previous known-good bundle, and run the previous image tag with the same mount and port. No database or state migration is required.

For startup failures, inspect `docker logs vireo-support-intelligence` and health output. Missing outputs mean rebuild the bundle with `scripts/package_dashboard_data.py`; schema/corruption errors mean rerun the pipeline and Stage 7 before packaging. Degraded AI status is expected without an evaluated model and does not block the dashboard.

Container build and run still require validation on a host with Docker before the image can be called deployable. See [deployment documentation](docs/technical/deployment.md) and the [production checklist](docs/technical/production_checklist.md).

Main folders:

- `src/vireo/`: ingestion, analytics, scoring, AI and evaluation logic.
- `configs/`: policy and stage configuration.
- `data/raw/`: source pack; preserve these files.
- `data/interim/`: generated analytical outputs.
- `app/`: dashboard and read-only presentation data preparation.
- `scripts/`: pipeline, AI contract smoke, and Stage 7 commands.
- `tests/`: unit and integration checks.
- `docs/technical/`: metric definitions, methodology, audits and stage findings.
- `docs/submission/`: evaluation memo and recording notes.

## Known limitations

- Stage 3 confidence intervals are approximate and assume independent tickets; clustered case-mix uncertainty is not implemented.
- There is no real-world ground truth for false-positive/false-negative rates and no genuine out-of-time validation.
- Stage 5 has no real predictions, model-quality evaluation, or real model usage cost. AI remains unavailable in the current run.
- 567 tickets lack effective roster context and are retained in aggregate metrics without peer comparison.
- Handle-time calculations retain valid extreme values; elapsed resolution time is not paid labor time.
- `agent_id` identifies the resolver, not necessarily the first responder; SLA is resolver-associated and not causal attribution.
- Source timestamp provenance, text-quality detection gaps, and ambiguous source relationships are documented in the forensic report.
- Cost exposure is observed population context, not agent-caused cost or guaranteed savings. Training costs are unavailable; no budget ROI is calculated.
- `docs/submission/submission-form.md` records that the original client submission form was unavailable; its questions are not reconstructed.

## Submission artifacts

See `docs/submission/memo.md`, `docs/submission/recording-notes.md`, and `docs/submission/submission-form.md`. The exact original submission form was not present in the repository, task attachments, or searched project workspace. No questions have been invented.
