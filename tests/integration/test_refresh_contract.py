import json
from pathlib import Path

import pytest

from scripts.refresh_release import RefreshRejected, refresh_release


def _reports(root: Path):
    interim = root / "data" / "interim"
    interim.mkdir(parents=True)
    for name in ("data_quality_report.json", "stage2_metrics_report.json", "stage3_analysis_report.json", "stage4_economics_report.json"):
        (interim / name).write_text(json.dumps({"status": "PASS", "checks": [{"status": "PASS"}]}), encoding="utf-8")
    (interim / "training_priority_report.json").write_text(json.dumps({"status": "PASS", "agents_evaluated": 2}), encoding="utf-8")


def test_failed_pipeline_stops_before_stage7_packaging_or_promotion(tmp_path):
    calls = []
    with pytest.raises(RefreshRejected, match="pipeline did not pass"):
        refresh_release(tmp_path, tmp_path / "releases", "failed-1",
                        pipeline_runner=lambda: {"status": "FAIL"},
                        stage7_runner=lambda *_: calls.append("stage7"),
                        package_runner=lambda *_: calls.append("package"),
                        promoter=lambda *_: calls.append("promote"))
    assert calls == []
    assert not (tmp_path / "releases").exists()


def test_failed_stage7_stops_before_packaging_or_promotion(tmp_path):
    _reports(tmp_path)
    calls = []
    with pytest.raises(RefreshRejected, match="Stage 7 evaluation did not pass"):
        refresh_release(tmp_path, tmp_path / "releases", "failed-2",
                        pipeline_runner=lambda: {"status": "PASS"},
                        stage7_runner=lambda *_: {"status": "FAIL"},
                        package_runner=lambda *_: calls.append("package"),
                        promoter=lambda *_: calls.append("promote"))
    assert calls == []
    assert not (tmp_path / "releases").exists()
