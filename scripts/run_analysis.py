"""Run the end-to-end Vireo support-intelligence pipeline."""

from pathlib import Path
import sys


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root / "src"))
    from vireo.pipeline.run import run_pipeline

    try:
        result = run_pipeline()
    except Exception as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1
    stage2 = result.get("stage2")
    print(f"Pipeline {result['status']}; Stage 1 forensic report: docs/technical/data_forensics.md")
    if stage2:
        print(f"Stage 2 {stage2['status']}; findings: docs/technical/stage2_findings.md; ticket metrics: {stage2['outputs']['ticket_metrics']['row_count']}")
    stage3 = result.get("stage3")
    if stage3:
        print(f"Stage 3 {stage3['status']}; findings: docs/technical/stage3_findings.md; comparison rows: {stage3['comparison_rows']}")
    stage4 = result.get("stage4")
    if stage4:
        print(f"Stage 4 {stage4['status']}; findings: docs/technical/stage4_findings.md; ticket rows: {stage4['ticket_rows']}")
    stage5 = result.get("stage5")
    if stage5:
        print(f"Stage 5 {stage5['ai_status']}; analyzed: {stage5.get('tickets_analyzed', 0)}; report: data/interim/ai_run_report.json")
    stage6 = result.get("stage6")
    if stage6:
        print(f"Stage 6 {stage6['status']}; agents: {stage6['agents_evaluated']}; high priority: {stage6['high_priority_count']}; report: data/interim/training_priority_report.json")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
