from pathlib import Path
import shutil

import pytest

from app.bundle_validation import validate_dashboard_bundle
from scripts.package_dashboard_data import package_dashboard_data
from scripts.promote_dashboard_bundle import promote_dashboard_bundle


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "interim"
HAS_SOURCE = (SOURCE / "training_priority.parquet").is_file()


@pytest.mark.skipif(not HAS_SOURCE, reason="Generated analytical outputs are not present")
def test_valid_bundle_installs_immutably_and_invalid_candidate_cannot_replace_it(tmp_path):
    candidate = tmp_path / "candidate"
    releases = tmp_path / "releases"
    package_dashboard_data(SOURCE, candidate)
    release = promote_dashboard_bundle(candidate, releases, "release-001")
    before = (release / "deployment_manifest.json").read_bytes()
    assert validate_dashboard_bundle(release)["status"] == "valid"

    invalid = tmp_path / "invalid"
    shutil.copytree(candidate, invalid)
    with (invalid / "agent_metrics.parquet").open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(ValueError, match="integrity|outputs"):
        promote_dashboard_bundle(invalid, releases, "release-001")
    assert (release / "deployment_manifest.json").read_bytes() == before
    assert validate_dashboard_bundle(release)["status"] == "valid"


def test_release_id_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match="release_id"):
        promote_dashboard_bundle(tmp_path / "missing", tmp_path / "releases", "../escape")
