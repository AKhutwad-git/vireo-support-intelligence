from pathlib import Path
import pyarrow.parquet as pq
from vireo.pipeline.run import run_pipeline

ROOT=Path(__file__).resolve().parents[2]


def test_optional_ai_pipeline_is_graceful_and_keeps_deterministic_outputs():
    result=run_pipeline()
    assert result["status"]=="PASS"
    assert result["stage4"]["ticket_rows"]==11750
    report=result["stage5"]
    assert report["status"]=="PASS"
    assert report["tickets_analyzed"]==0
    assert report["evaluation"]["model_accuracy"] is None
    assert report["evaluation"]["human_reviewed_sample_size"]==20
    assert report["tickets_selected"]<=250
    for name in ("ai_ticket_analysis","ai_agent_diagnostics","ai_peer_diagnostics","ai_evaluation"):
        assert pq.read_table(ROOT/"data"/"interim"/f"{name}.parquet").num_rows==report["outputs"][name]["row_count"]
    assert pq.read_table(ROOT/"data"/"interim"/"ticket_economics.parquet").num_rows==11750
