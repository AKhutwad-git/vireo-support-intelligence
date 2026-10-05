"""Run Stage 7 reconciliations and robustness evaluation."""
from pathlib import Path
import sys


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))
    from vireo.evaluation.runner import run_stage7

    try:
        report = run_stage7(project_root)
    except Exception as exc:
        print(f"Stage 7 evaluation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Stage 7 {report['status']}; production readiness: {report['production_readiness_verdict']}")
    print("Report: data/interim/stage7_validation_report.json")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
