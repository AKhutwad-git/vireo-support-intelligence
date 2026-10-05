"""Validate and install a dashboard bundle as an immutable release artifact."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import tempfile

from app.bundle_validation import validate_dashboard_bundle


_RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def promote_dashboard_bundle(candidate: Path, release_root: Path, release_id: str) -> Path:
    candidate, release_root = candidate.resolve(), release_root.resolve()
    if not _RELEASE_ID.fullmatch(release_id) or release_id in {".", ".."}:
        raise ValueError("release_id must use 1-64 letters, numbers, dots, underscores, or hyphens")
    validate_dashboard_bundle(candidate)
    destination = release_root / release_id
    if destination.exists():
        raise FileExistsError(f"Immutable release already exists: {destination}")
    release_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{release_id}-", dir=release_root))
    try:
        shutil.rmtree(staging)
        shutil.copytree(candidate, staging)
        validate_dashboard_bundle(staging)
        # Same-filesystem directory rename publishes a complete, validated bundle
        # under a new immutable name; it never replaces an existing release.
        staging.rename(destination)
        return destination
    except Exception:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--release-root", type=Path, default=Path("data/releases"))
    args = parser.parse_args()
    try:
        destination = promote_dashboard_bundle(args.candidate, args.release_root, args.release_id)
    except Exception as exc:
        parser.exit(1, f"Bundle promotion refused: {exc}\n")
    print(f"Validated immutable release installed: {destination}")
    print("Activation is a separate, operator-gated deployment step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
