from pathlib import Path
import pyarrow.parquet as pq
from vireo.pipeline.run import run_pipeline

ROOT=Path(__file__).resolve().parents[2]


def test_stage4_economics_outputs_and_reconciliation():
    result=run_pipeline()
    assert result["status"]=="PASS"
    report=result["stage4"]
    assert report["status"]=="PASS"
    assert report["ticket_rows"]==11750
    assert report["upstream_audit"]["ticket_grain_reconciles"]
    assert report["checks"]["all_monetary_exposures_nonnegative"]
    assert report["checks"]["scenario_opportunity_within_driver_exposure"]
    for name in ("ticket_economics","agent_economics","period_economics","channel_economics","team_economics","opportunity_scenarios"):
        assert pq.read_table(ROOT/"data"/"interim"/f"{name}.parquet").num_rows==report["outputs"][name]["row_count"]
