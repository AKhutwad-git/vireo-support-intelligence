import json
from pathlib import Path
import pyarrow.parquet as pq
from vireo.pipeline.run import run_pipeline


ROOT=Path(__file__).resolve().parents[2]


def test_stage6_runs_without_ai_and_preserves_upstream_grain():
    result=run_pipeline()
    assert result["status"]=="PASS"
    assert result["stage4"]["ticket_rows"]==11750
    assert result["stage5"]["tickets_analyzed"]==0
    stage6=result["stage6"]
    assert stage6["status"]=="PASS" and stage6["agents_evaluated"]==44
    assert stage6["ai_evidence_status"]=="unavailable"
    assert pq.read_table(ROOT/"data"/"interim"/"training_priority.parquet").num_rows==44
    report=json.loads((ROOT/"data"/"interim"/"training_priority_report.json").read_text(encoding="utf-8"))
    assert report["high_priority_count"]==0
    assert pq.read_table(ROOT/"data"/"interim"/"ticket_metrics.parquet").num_rows==11750
