from pathlib import Path
import pyarrow.parquet as pq
from vireo.pipeline.run import run_pipeline

ROOT = Path(__file__).resolve().parents[2]

def test_stage2_pipeline_writes_audited_metrics_without_multiplying_tickets():
    result = run_pipeline()
    assert result["status"] == "PASS"
    stage2 = result["stage2"]
    assert stage2["status"] == "PASS"
    for name in ("ticket_metrics", "agent_metrics", "agent_assignment_metrics", "period_metrics", "channel_metrics", "team_metrics"):
        path = ROOT / "data" / "interim" / f"{name}.parquet"
        assert path.is_file()
        assert pq.read_table(path).num_rows == stage2["outputs"][name]["row_count"]
    assert stage2["outputs"]["ticket_metrics"]["row_count"] == stage2["stage1_input_audit"]["ticket_rows"]
    assert stage2["stage1_input_audit"]["ticket_rows"] == 11750
    assert all(check["status"] == "PASS" for check in stage2["checks"])
    assignment_fields = set(pq.read_schema(ROOT / "data" / "interim" / "agent_assignment_metrics.parquet").names)
    assert {"agent_id", "agent_team", "agent_tier", "agent_site", "agent_shift", "reporting_month", "period_type"} <= assignment_fields
    metrics = pq.read_table(ROOT / "data" / "interim" / "ticket_metrics.parquet").to_pylist()
    assert sum(row["attendance_flag"] for row in metrics) == 11183
    assert sum(row["agent_assignment_flag"] != "matched" for row in metrics) == 567
    assert (ROOT / "docs" / "technical" / "metric_definitions.md").is_file()
    assert (ROOT / "docs" / "technical" / "stage2_findings.md").is_file()
