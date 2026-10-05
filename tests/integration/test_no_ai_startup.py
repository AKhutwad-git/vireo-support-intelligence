from pathlib import Path

import pytest

from app.runtime_health import check_dashboard_health
from scripts.package_dashboard_data import package_dashboard_data
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "interim"
HAS_SOURCE = (SOURCE / "training_priority.parquet").is_file() and (SOURCE / "stage4_economics_report.json").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_dashboard_health_degrades_gracefully_when_ai_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.delenv("VIREO_AI_API_KEY", raising=False)
    target = tmp_path / "bundle"
    package_dashboard_data(SOURCE, target)
    result = check_dashboard_health(ROOT, target)
    assert result["status"] == "degraded"
    assert result["deterministic_data"] == "valid"
    assert result["ai_status"] == "unavailable"
    assert result["agent_count"] == 44
    monkeypatch.setenv("VIREO_INTERIM_DIR", str(target))
    app = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=30).run()
    assert not app.exception
    next(widget for widget in app.radio if widget.label == "Navigate").set_value("Agent Detail").run()
    assert not app.exception
    assert any("AI diagnostics unavailable" in element.value for element in app.info)
