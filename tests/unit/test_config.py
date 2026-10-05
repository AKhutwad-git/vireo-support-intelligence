from pathlib import Path

import pytest

from vireo import __version__
from vireo.pipeline.run import load_config


ROOT = Path(__file__).resolve().parents[2]


def test_project_configuration_loads_without_secret_values():
    config = load_config(ROOT / "configs" / "config.yaml")
    assert config["ai"]["enabled"] is False
    assert config["ai"]["api_key_env"] == "VIREO_AI_API_KEY"
    assert config["stage6"]["require_interval_excludes_zero"] is True


def test_invalid_yaml_has_clear_configuration_error(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("bad: [", encoding="utf-8")
    with pytest.raises(ValueError, match="Could not load configuration"):
        load_config(path)


def test_application_version_is_available():
    assert __version__ == "0.1.0"
