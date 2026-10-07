"""Validation for immutable dashboard release bundles."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from vireo import __version__
from app.dashboard_data import load_dashboard_data


MANIFEST_NAME = "deployment_manifest.json"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dashboard_bundle(bundle_dir: str | Path, *, check_application_version: bool = True) -> dict:
    """Check manifest inventory/hashes and the same schemas/joins used by the app."""
    root = Path(bundle_dir).resolve()
    manifest_path = root / MANIFEST_NAME
    if not root.is_dir():
        raise FileNotFoundError(f"Dashboard bundle directory is missing: {root}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Required bundle manifest is missing: {MANIFEST_NAME}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Bundle manifest is unreadable: {exc}") from exc
    if manifest.get("bundle_version") != 1:
        raise ValueError("Unsupported dashboard bundle_version")
    if check_application_version and manifest.get("application_version") != __version__:
        raise ValueError("Bundle application_version does not match this application")
    if manifest.get("contains_raw_source_data") is not False:
        raise ValueError("Bundle manifest must explicitly state contains_raw_source_data=false")

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Bundle manifest files inventory is missing or invalid")
    actual = {path.name for path in root.iterdir() if path.is_file() and path.name != MANIFEST_NAME}
    if set(files) != actual:
        raise ValueError("Bundle manifest file inventory does not match files on disk")
    for name, metadata in files.items():
        if not _SAFE_NAME.fullmatch(name) or Path(name).name != name:
            raise ValueError(f"Unsafe bundle filename in manifest: {name}")
        path = root / name
        if not path.is_file():
            raise FileNotFoundError(f"Manifest file is missing: {name}")
        if not isinstance(metadata, dict) or not metadata.get("purpose") or not metadata.get("format"):
            raise ValueError(f"Manifest purpose/format is missing for {name}")
        if metadata.get("schema_version") != 1:
            raise ValueError(f"Unsupported schema_version for {name}")
        if metadata.get("size_bytes") != path.stat().st_size or metadata.get("sha256") != sha256_file(path):
            raise ValueError(f"Bundle integrity check failed for {name}")

    data = load_dashboard_data(root, interim_dir=root)
    row_counts = manifest.get("table_row_counts", {})
    for table_name, expected in row_counts.items():
        name = Path(table_name).name
        if name not in files or files[name].get("row_count") != expected:
            raise ValueError(f"Manifest row count is inconsistent for {name}")
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict) or not provenance.get("source_snapshot_sha256") or not provenance.get("decision_config_sha256"):
        raise ValueError("Bundle provenance is incomplete")
    return {"status": "valid", "application_version": manifest["application_version"],
            "agent_count": len(data["agents"]), "validated_output_count": 7,
            "manifest": manifest}
