# Release Record

This records the historical `final-20261006-04` application/bundle pair. The later candidate currently running on ports 8501 and 8505 is not represented by this source SHA or test count; its local verification is recorded in `docs/technical/final_acceptance.md`. Neither record is target-host deployment approval.

| Field | Value |
| --- | --- |
| Release ID | `final-20261006-04` |
| Application version | `0.1.0` |
| Git source commit SHA | `4b16ca55fa57a19214b6e3b1164b9ef24f4e000c` |
| Pipeline worktree dirty | `false` |
| Stage 7 verdict | `VALIDATED WITH MATERIAL LIMITATIONS` |
| Stage 5 / AI | Unavailable; 0 provider requests; 0 real predictions |
| Tests | `119 passed, 1 skipped, 0 failed` |
| Bundle validation | PASS; 44 agents; schema, joins, inventory, and SHA-256 checks passed |
| Image tag | `vireo-support-intelligence:0.1.0-final-20261006-04` |
| Docker image ID | `sha256:58101c6cd0297a4ccd0d6eddd924f993eeec83477e704fb7b61e7bd014c68246` |
| Local image/repository digest | `sha256:58101c6cd0297a4ccd0d6eddd924f993eeec83477e704fb7b61e7bd014c68246` |
| Exact-SHA CI | `PASS` — `python-tests` completed successfully for the source SHA; [run 37368397844](https://github.com/AKhutwad-git/vireo-support-intelligence/actions/runs/37368397844/job/111959100327) |
| Target-host deployment | `NOT VERIFIED` |

## Local runtime evidence

Candidate `vireo-final-20261006-04` was run on `127.0.0.1:8504` from the image and bundle above. It ran as `vireo` UID/GID 999. Docker health was `healthy`; semantic health was `degraded` because AI diagnostics were unavailable, with deterministic data valid, 44 agents, six outputs validated, and the process alive. The Streamlit health endpoint returned HTTP 200 and the dashboard rendered. The bundle mount was read-only. This is local verification only; external hosting, target-host security, centralized monitoring/paging, and production approval are not evidenced.
