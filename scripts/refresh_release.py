"""Run analysis, Stage 7, package validation, and immutable release installation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from app.bundle_validation import validate_dashboard_bundle
from scripts.package_dashboard_data import package_dashboard_data
from scripts.promote_dashboard_bundle import promote_dashboard_bundle
from vireo.evaluation.runner import run_stage7
from vireo.pipeline.run import run_pipeline


class RefreshRejected(RuntimeError):
    pass


def _required_report(root: Path, relative: str, expected_status: str = "PASS") -> dict:
    path = root / "data" / "interim" / relative
    if not path.is_file():
        raise RefreshRejected(f"Required pipeline report is missing: {relative}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("status") != expected_status:
        raise RefreshRejected(f"{relative} status is {report.get('status')!r}, expected {expected_status}")
    return report


def refresh_release(project_root: Path, release_root: Path, release_id: str, *,
                    pipeline_runner=run_pipeline, stage7_runner=run_stage7,
                    package_runner=package_dashboard_data, promoter=promote_dashboard_bundle) -> dict:
    """Build an isolated candidate and install only after all data gates pass.

    This stores an immutable release bundle; it never switches the running service.
    Deployment activation remains an explicit operator step.
    """
    root, release_root = project_root.resolve(), release_root.resolve()
    pipeline = pipeline_runner()
    if pipeline.get("status") != "PASS":
        raise RefreshRejected("Stages 1-6 pipeline did not pass; no candidate was packaged")
    quality = _required_report(root, "data_quality_report.json")
    stage6 = _required_report(root, "training_priority_report.json")
    for report_name in ("stage2_metrics_report.json", "stage3_analysis_report.json", "stage4_economics_report.json"):
        _required_report(root, report_name)
    if not quality.get("checks"):
        raise RefreshRejected("Data-quality report has no recorded validation checks")
    if int(stage6.get("agents_evaluated", 0)) <= 0:
        raise RefreshRejected("Stage 6 report has no evaluated agents")

    stage7 = stage7_runner(root)
    if stage7.get("status") != "PASS":
        raise RefreshRejected("Stage 7 evaluation did not pass; no candidate was packaged")
    stage7_report = _required_report(root, "stage7_validation_report.json")
    upstream = stage7_report.get("upstream_audit", {}).get("stage1", {})
    if upstream.get("status") != "PASS" or upstream.get("ticket_rows") != upstream.get("unique_ticket_ids"):
        raise RefreshRejected("Stage 7 did not confirm valid ticket grain and unique ticket IDs")

    release_root.mkdir(parents=True, exist_ok=True)
    candidate = release_root / f".candidate-{release_id}-{uuid.uuid4().hex}"
    try:
        package_runner(root / "data" / "interim", candidate)
        bundle = validate_dashboard_bundle(candidate)
        release_path = promoter(candidate, release_root, release_id)
    finally:
        if candidate.exists():
            shutil.rmtree(candidate, ignore_errors=True)
    return {"status": "PASS", "release_id": release_id, "release_path": str(release_path),
            "application_version": bundle["application_version"], "agent_count": bundle["agent_count"],
            "pipeline_status": pipeline["status"], "stage7_status": stage7["status"],
            "stage7_readiness": stage7_report.get("production_readiness_verdict"),
            "activation": "not_performed"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--release-root", type=Path, default=ROOT / "data" / "releases")
    args = parser.parse_args()
    try:
        result = refresh_release(ROOT, args.release_root, args.release_id)
    except Exception as exc:
        parser.exit(1, f"Refresh rejected: {exc}\n")
    print(json.dumps(result, ensure_ascii=False))
    print("No running service was changed; activate this immutable release only after release gates pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
