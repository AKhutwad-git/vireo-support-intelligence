# Vireo Support Intelligence

A deterministic support-operations analysis and decision-support dashboard prepared for the Banao Technologies evaluation. It reports support performance, Tier-safe peer comparisons, observed economics, and evidence-gated training status. It does not infer agent causality or manufacture a bottom-ten training recommendation.

## Current result

The current source pack contains 11,750 tickets from January 2025 through June 2026. Stage 6 reports **0 defensible training candidates and 44 monitor agents**. No agent meets the configured interval-based evidence threshold. Three point-estimate-only names from Stage 7 sensitivity (A3015, A3021, A3026) are exploratory and are not recommendations.

The Overview also provides **Bottom 10 — Review Queue** and **Top 5 — Bonus Review** as descriptive management-review lists ordered by a transparent composite of Tier-safe, case-mix-adjusted gaps. These lists do not change Stage 6 status and do not recommend retraining or determine bonuses. The current evidence supports allocating **₹0 of the ₹4,00,000 Q3 training budget to agent-specific retraining** and reserving the balance pending stronger evidence or targeted process investigation.

The proposed numeric operational goal is to reduce the observed resolver-associated first-response SLA breach rate by **1 percentage point**, from **9.06% to 8.06%**. On the same 11,750-ticket denominator, the policy-credit sensitivity is approximately **₹41,125** (`11,750 × 0.01 × ₹350 per breach`). This is a proposed target and same-population sensitivity, not a forecast, causal estimate, realized savings, or guaranteed credit reduction.

Stage 7 passed 12 independent metric reconciliations, eight synthetic decision scenarios, 220 explanation checks, and reproducibility checks. Its readiness verdict is **VALIDATED WITH MATERIAL LIMITATIONS**. The intervals are approximate; there is no agent-quality ground truth, clustered case-mix uncertainty, or genuine out-of-time validation. Stage 5's bounded real Gemini evaluation attempted 20 requests: only 3 produced schema-valid predictions, all matching their labels; 5 failed schema validation and 12 received HTTP 429. This does not establish overall model accuracy or production readiness.

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

Place the separately supplied source pack in local `data/raw/`; do not edit source files in place. Raw client records are not committed to this Git repository; only the source-pack README is tracked. Required schemas and policy context are documented in `data/raw/README.txt`. The analytical pipeline writes generated Parquet/JSON files into ignored `data/interim/` and technical findings into `docs/technical/`.

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

The dashboard reads generated outputs; it does not rerun analysis on page refresh. It provides Overview, Agents, Agent Detail, an optional Product & Orders page when the new Stage 4 aggregates are present, and Methodology / Trust. The Product & Orders page shows descriptive product/SKU, order-channel, sufficiently supported lot, and agent exposure summaries; it does not change training decisions. Overview surfaces the business goal, budget decision, and review queues. The Agents page supports filters and CSV downloads. Stage 7 validation summary JSON is available on Methodology / Trust.

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
  → Stage 4 bounded product/order root-cause aggregates (row-safe order linkage)
  → Stage 5 optional AI diagnostics
  → Stage 6 deterministic training-priority decisions
  → Stage 7 reconciliation and robustness evaluation
  → app/dashboard_data.py validated presentation views and exports
  → app/streamlit_app.py Streamlit presentation
```

## Deployment (single container)

The container serves the dashboard only. It does not include raw source data or run Stages 1–7 at startup. Deployment uses **Option A: a separately supplied, precomputed reduced dashboard bundle**. The controlled release path gates packaging on Stages 1–6 and Stage 7, validates a hashed manifest, and installs an immutable release without activating the service. The Git repository contains source and release tooling; generated bundles live under ignored local `data/releases/` and are not included in a source checkout.

Run the example below in Bash; choose a unique ID for each release. The refresh command prints the installed path and does not activate a service:

```bash
release_id="final-$(date -u +%Y%m%dT%H%M%SZ)"
python -m uv run python scripts/refresh_release.py --release-id "$release_id"
python -m uv run python -c "from app.bundle_validation import validate_dashboard_bundle; print(validate_dashboard_bundle('data/releases/$release_id')['status'])"
image_tag="vireo-support-intelligence:0.1.0-$release_id"
docker build -t "$image_tag" .
docker run -d --name vireo-candidate -p 8502:8501 \
  --mount "type=bind,source=$(pwd)/data/releases/$release_id,target=/app/runtime-data,readonly" \
  "$image_tag"
```

PowerShell equivalent:

```powershell
$releaseId = "final-$((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ'))"
python -m uv run python scripts/refresh_release.py --release-id $releaseId
python -m uv run python -c "from app.bundle_validation import validate_dashboard_bundle; print(validate_dashboard_bundle('data/releases/$releaseId')['status'])"
$imageTag = "vireo-support-intelligence:0.1.0-$releaseId"
docker build -t $imageTag .
$bundle = (Resolve-Path "data/releases/$releaseId").Path
docker run -d --name vireo-candidate -p 8502:8501 `
  --mount "type=bind,source=$bundle,target=/app/runtime-data,readonly" `
  $imageTag
```

Open `http://localhost:8501`. The container runs as an unprivileged user. CORS and XSRF protections stay enabled. Check health with:

```bash
docker inspect --format '{{.State.Health.Status}}' vireo-support-intelligence
```

`python -m app.healthcheck` emits JSON status: `healthy`, `degraded`, or `unhealthy`. AI absence yields `degraded` while deterministic functions remain available; Docker treats degraded as a functioning process. Missing/corrupt required outputs, invalid bundle hashes, or an unavailable Streamlit health endpoint produce `unhealthy`.

### Deployment configuration

| Variable | Secret | Purpose |
|---|---:|---|
| `VIREO_INTERIM_DIR` | No | Dashboard bundle directory. Defaults to project `data/interim`; container sets `/app/runtime-data`. Relative local paths resolve from the project root. |
| `VIREO_LOG_LEVEL` | No | Python log threshold; defaults to `INFO`. |
| `VIREO_AI_API_KEY` | **Yes** | Optional Stage 5 provider key for the analysis pipeline. Not required by the dashboard container and never baked into the image. |

Configure secrets through a deployment platform's secret store or process environment, never the repository, image, or logs. Logs report version, validation/health state, row counts, and errors; they do not contain customer messages, agent notes, authorization headers, or credential values.

### Runtime data and recovery

The image contains application code and locked runtime libraries only. `data/raw/` is needed to rebuild analysis outside the serving container. `data/interim/` is generated and may contain ticket-level content; the container receives only the reduced immutable release bundle. Keep versioned copies of the image digest and matching bundle. To roll back, use the prior image and bundle pair with the deployment platform's rollback process. No database or state migration is required.

For startup failures, inspect `docker logs vireo-candidate` and health output. Missing outputs mean rebuild through `scripts/refresh_release.py` with a new release ID; schema/corruption errors mean rerun the pipeline and Stage 7 before packaging. Degraded AI status is expected without an evaluated model and does not block the dashboard. These steps provide local Docker deployment tooling; external hosting and centralized monitoring/paging are not configured or verified here.

See the [deployment documentation](docs/technical/deployment.md), [operations guide](docs/technical/operations.md), [release process](docs/technical/release_process.md), [incident runbook](docs/technical/incident_response.md), and [Stage 10 acceptance record](docs/technical/final_acceptance.md).

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
- `docs/technical/product_order_root_cause_analysis.md`: deterministic product/order findings, denominators, and limitations for the supplied source pack.
- `docs/technical/task1_remediation_audit.md`: pre-change requirement audit and Prompt 2 AI gap.

## Known limitations

- Stage 3 confidence intervals are approximate and assume independent tickets; clustered case-mix uncertainty is not implemented.
- There is no real-world ground truth for false-positive/false-negative rates and no genuine out-of-time validation.
- The bounded Stage 5 Gemini evaluation attempted 20 requests: 3 predictions passed schema validation and matched labels, 5 failed schema validation, and 12 received HTTP 429. Only 3/20 cases were scored, so 3/3 is not overall model accuracy. Billed cost and complete usage-based cost are unknown; this does not establish model quality or production readiness.
- 567 tickets lack effective roster context and are retained in aggregate metrics without peer comparison.
- Handle-time calculations retain valid extreme values; elapsed resolution time is not paid labor time.
- `agent_id` identifies the resolver, not necessarily the first responder; SLA is resolver-associated and not causal attribution.
- Source timestamp provenance, text-quality detection gaps, and ambiguous source relationships are documented in the forensic report.
- Cost exposure is observed population context, not agent-caused cost or guaranteed savings. Training costs are unavailable; no budget ROI is calculated.
- `docs/submission/submission-form.md` contains responses to the actual questions included with the Task 1 brief; unknown personal/tool details and unverified recording/Drive link access are identified explicitly. The GitHub repository page was reachable and labeled Public when checked on 2026-10-07, but the current local candidate changes are not yet committed or pushed.

## Submission artifacts

See `docs/submission/memo.md`, `docs/submission/recording-notes.md`, `docs/submission/submission-form.md`, and `docs/submission/release-record.md`. The response form follows the actual Task 1 questions supplied with the brief. The release record names the ignored local bundle and locally built image; a fresh checkout must regenerate its own unique release bundle through the documented workflow.
