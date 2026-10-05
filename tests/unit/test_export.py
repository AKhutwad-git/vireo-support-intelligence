import csv
import io
from pathlib import Path
import pytest

from app.dashboard_data import EXPORT_COLUMNS, export_csv, load_dashboard_data


ROOT = Path(__file__).resolve().parents[2]
HAS_SOURCE = (ROOT / "data" / "interim" / "training_priority.parquet").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_csv_exports_have_expected_columns_and_preserve_rows():
    data = load_dashboard_data(ROOT)
    expected = {
        "training_priority": "training_priority",
        "agent_performance": "agent_performance",
        "agent_economics": "agent_economics",
    }
    for export_name, _ in expected.items():
        content = export_csv(data["agents"], export_name).decode("utf-8-sig")
        parsed = list(csv.DictReader(io.StringIO(content)))
        assert len(parsed) == len(data["agents"])
        assert list(parsed[0]) == EXPORT_COLUMNS[export_name]
        assert "Unnamed: 0" not in parsed[0]


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_priority_export_preserves_stage6_status_and_rank():
    data = load_dashboard_data(ROOT)
    parsed = list(csv.DictReader(io.StringIO(export_csv(data["agents"], "training_priority").decode("utf-8-sig"))))
    assert {row["priority_status"] for row in parsed} == {row["priority_status"] for row in data["agents"]}
    assert [row["priority_rank"] for row in parsed] == ["" if row["priority_rank"] is None else str(row["priority_rank"]) for row in data["agents"]]
