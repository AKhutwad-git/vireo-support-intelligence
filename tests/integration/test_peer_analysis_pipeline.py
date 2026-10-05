from pathlib import Path
import pyarrow.parquet as pq
from vireo.pipeline.run import run_pipeline

ROOT=Path(__file__).resolve().parents[2]

def test_peer_analysis_outputs_reconcile_and_preserve_stage_boundaries():
    result=run_pipeline()
    assert result["status"]=="PASS"
    assert result["stage2"]["status"]=="PASS"
    stage3=result["stage3"]
    assert stage3["status"]=="PASS"
    assert stage3["stage2_audit"]["ticket_rows"]==11750
    assert stage3["stage2_audit"]["distinct_roster_agents"]==44
    assert stage3["stage2_audit"]["completed_csat_response_count"]==4947
    assert stage3["stage2_audit"]["populated_open_pending_scores"]==249
    assert stage3["stage2_audit"]["open_pending_scores_excluded_from_primary_csat"] is True
    for name in ("peer_groups","case_mix_metrics","adjusted_agent_metrics","agent_comparison"):
        path=ROOT/"data"/"interim"/f"{name}.parquet"
        assert path.is_file()
        assert pq.read_table(path).num_rows==stage3["outputs"][name]["row_count"]
    assert all(len(group["tiers"])==1 for group in stage3["peer_groups"])
    assert stage3["ticket_rows_preserved"]==11750
    assert (ROOT/"docs"/"technical"/"peer_and_case_mix.md").is_file()
    assert (ROOT/"docs"/"technical"/"stage3_findings.md").is_file()
    assert (ROOT/"data"/"interim"/"stage3_analysis_report.json").is_file()
