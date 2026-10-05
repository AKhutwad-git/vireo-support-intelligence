from pathlib import Path

import pytest

from vireo.pipeline.run import run_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
EXPECTED = ("tickets.csv", "agents.csv", "customers.csv", "orders.csv", "products.csv", "support-policy.pdf", "email-thread.txt", "README.txt")
HAS_COMPLETE_PACK = all((RAW_DIR / name).is_file() for name in EXPECTED)


def test_missing_task_pack_is_reported_clearly():
    if HAS_COMPLETE_PACK:
        pytest.skip("Complete task pack is present; run full-pack integration case instead")
    result = run_pipeline()
    assert result["status"] == "FAIL"
    assert result["missing_files"]
    assert (PROJECT_ROOT / "docs" / "technical" / "data_forensics.md").is_file()


@pytest.mark.skipif(not HAS_COMPLETE_PACK, reason="Real raw task pack is not available")
def test_real_task_pack_pipeline_produces_canonical_outputs():
    result = run_pipeline()
    assert result["status"] == "PASS"
    assert result["processed"]["outputs"]
    for output in result["processed"]["outputs"].values():
        assert Path(output["path"]).is_file()
        assert output["row_count"] >= 0
    import pyarrow.parquet as pq
    tickets = pq.read_table(result["processed"]["outputs"]["tickets"]["path"]).to_pylist()
    assert len(tickets) == result["processed"]["outputs"]["tickets"]["row_count"]
    assert sum(bool(row["signup_anomaly_flag"]) for row in tickets) > 0
    assert all("created_at_raw" in row for row in tickets)
