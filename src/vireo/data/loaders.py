"""Deterministic loaders for the supplied raw task pack."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


EXPECTED_FILES = (
    "tickets.csv", "agents.csv", "customers.csv", "orders.csv", "products.csv",
    "support-policy.pdf", "email-thread.txt", "README.txt",
)


class SourceLoadError(ValueError):
    """A source file exists but cannot be read in the expected format."""


def check_file_presence(raw_dir: Path, expected_files: tuple[str, ...] = EXPECTED_FILES) -> dict[str, bool]:
    return {name: (raw_dir / name).is_file() for name in expected_files}


def load_csv(path: Path, *, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    try:
        with path.open("r", encoding=encoding, newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise SourceLoadError(f"CSV has no header row: {path}")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise SourceLoadError(f"CSV contains duplicate column names: {path}")
            if any(name is None or not name.strip() for name in reader.fieldnames):
                raise SourceLoadError(f"CSV contains a blank column name: {path}")
            rows = []
            for line_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise SourceLoadError(f"CSV row has a different number of fields than its header at {path}:{line_number}")
                rows.append(dict(row))
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SourceLoadError(f"Could not read CSV {path}: {exc}") from exc


def load_sources(raw_dir: Path, file_map: dict[str, str] | None = None) -> dict[str, Any]:
    """Read expected inputs; non-CSV files are preserved as source text or inventory metadata."""
    names = file_map or {name.rsplit(".", 1)[0].replace("-", "_"): name for name in EXPECTED_FILES}
    sources: dict[str, Any] = {}
    for name, filename in names.items():
        path = raw_dir / filename
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".csv":
            sources[name] = load_csv(path)
        elif suffix == ".txt":
            try:
                sources[name] = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                raise SourceLoadError(f"Could not read text source {path}: {exc}") from exc
        elif suffix == ".pdf":
            sources[name] = {"path": filename, "size_bytes": path.stat().st_size, "content_extracted": False}
    return sources
