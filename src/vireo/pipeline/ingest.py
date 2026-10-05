"""Load source files and perform initial, source-driven validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from vireo.data.loaders import EXPECTED_FILES, check_file_presence, load_sources
from vireo.data.schemas import schema_as_dicts
from vireo.data.validators import CheckResult, validate_relationship, validate_table
from vireo.data.schemas import SOURCE_CONTRACTS


def ingest(raw_dir: Path, config: dict[str, Any]) -> dict[str, Any]:
    presence = check_file_presence(raw_dir)
    sources = load_sources(raw_dir)
    dataset_config = config.get("datasets", {})
    tables = {name: value for name, value in sources.items() if isinstance(value, list)}
    schemas = {name: schema_as_dicts(rows) for name, rows in tables.items()}
    checks: list[CheckResult] = []
    missing = [name for name, found in presence.items() if not found]
    checks.append(CheckResult("source_file_presence", "PASS" if not missing else "FAIL", "All expected source files found" if not missing else "Missing source files: " + ", ".join(missing), count=len(missing)))
    for name, rows in tables.items():
        contract = SOURCE_CONTRACTS.get(name, {})
        spec = dataset_config.get(name, {})
        checks.extend(validate_table(name, rows, required_columns=contract.get("required", spec.get("required_columns")), key=contract.get("key") if name != "agents" else None, date_columns=contract.get("dates", spec.get("date_columns")), numeric_ranges=spec.get("numeric_ranges"), categories=spec.get("categories")))
    for relation in config.get("relationships", []):
        parent, child = relation["parent"], relation["child"]
        if parent in tables and child in tables:
            checks.extend(validate_relationship(parent, child, tables[parent], tables[child], relation["parent_key"], relation["child_key"], unique_child=relation.get("unique_child", False)))
        else:
            checks.append(CheckResult("referential_integrity", "WARNING", f"Relationship not checked; missing table: {parent if parent not in tables else child}", child))
    return {"presence": presence, "sources": sources, "tables": tables, "schemas": schemas, "checks": checks, "missing_files": missing}
