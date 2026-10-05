"""Small deterministic quality checks with explicit PASS/WARNING/FAIL outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str
    dataset: str | None = None
    count: int | None = None


def _result(name: str, passed: bool, message: str, dataset: str | None = None, count: int | None = None) -> CheckResult:
    return CheckResult(name, "PASS" if passed else "FAIL", message, dataset, count)


def validate_required_columns(dataset: str, rows: list[dict[str, Any]], required: list[str]) -> list[CheckResult]:
    missing = sorted(set(required) - (set(rows[0]) if rows else set()))
    return [_result("required_columns", not missing, "Required columns present" if not missing else f"Missing required columns: {', '.join(missing)}", dataset, len(missing))]


def validate_key(dataset: str, rows: list[dict[str, Any]], key: str) -> list[CheckResult]:
    missing_values = sum(row.get(key) in (None, "") for row in rows)
    values = [row.get(key) for row in rows if row.get(key) not in (None, "")]
    duplicates = len(values) - len(set(values))
    return [
        _result("critical_identifier_nulls", missing_values == 0, f"{missing_values} rows have a null/blank {key}", dataset, missing_values),
        _result("duplicate_key", duplicates == 0, f"{duplicates} duplicate {key} values", dataset, duplicates),
    ]


def validate_dates(dataset: str, rows: list[dict[str, Any]], columns: list[str] | None = None) -> list[CheckResult]:
    if not rows:
        return []
    selected = columns if columns is not None else [name for name in rows[0] if any(token in name.lower() for token in ("date", "time", "timestamp"))]
    output: list[CheckResult] = []
    formats = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z")
    for column in selected:
        invalid = 0
        for row in rows:
            value = row.get(column)
            if value in (None, ""):
                continue
            valid = False
            for fmt in formats:
                try:
                    datetime.strptime(str(value).strip(), fmt)
                    valid = True
                    break
                except ValueError:
                    pass
            if not valid:
                try:
                    datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
                    valid = True
                except ValueError:
                    try:
                        date.fromisoformat(str(value).strip())
                        valid = True
                    except ValueError:
                        pass
            invalid += not valid
        output.append(_result("date_parse", invalid == 0, f"{invalid} invalid values in {column}", dataset, invalid))
    return output


def validate_table(dataset: str, rows: list[dict[str, Any]], *, required_columns: list[str] | None = None, key: str | None = None, date_columns: list[str] | None = None, numeric_ranges: dict[str, dict[str, float]] | None = None, categories: dict[str, list[str]] | None = None) -> list[CheckResult]:
    checks: list[CheckResult] = []
    if required_columns is not None:
        checks.extend(validate_required_columns(dataset, rows, required_columns))
    if key:
        checks.extend(validate_key(dataset, rows, key))
    checks.extend(validate_dates(dataset, rows, date_columns))
    checks.extend(validate_numeric_ranges(dataset, rows, numeric_ranges or {}))
    checks.extend(validate_categories(dataset, rows, categories or {}))
    if rows and len(rows) > 0:
        checks.append(CheckResult("row_count", "PASS", f"Observed {len(rows)} rows", dataset, len(rows)))
    return checks


def validate_relationship(parent: str, child: str, parent_rows: list[dict[str, Any]], child_rows: list[dict[str, Any]], parent_key: str, child_key: str, *, unique_child: bool = False) -> list[CheckResult]:
    parent_key_values = [row.get(parent_key) for row in parent_rows if row.get(parent_key) not in (None, "")]
    parent_values = set(parent_key_values)
    child_values = [row.get(child_key) for row in child_rows if row.get(child_key) not in (None, "")]
    orphans = sum(value not in parent_values for value in child_values)
    duplicate_parent_keys = len(parent_key_values) - len(parent_values)
    results = [
        _result("parent_key_uniqueness", duplicate_parent_keys == 0, f"{duplicate_parent_keys} duplicate {parent}.{parent_key} values", parent, duplicate_parent_keys),
        _result("referential_integrity", orphans == 0, f"{orphans} {child}.{child_key} values do not match {parent}.{parent_key}", child, orphans),
    ]
    if unique_child:
        duplicates = len(child_values) - len(set(child_values))
        results.append(_result("relationship_cardinality", duplicates == 0, f"{duplicates} duplicate child foreign-key values", child, duplicates))
    return results


def validate_numeric_ranges(dataset: str, rows: list[dict[str, Any]], ranges: dict[str, dict[str, float]]) -> list[CheckResult]:
    output: list[CheckResult] = []
    for column, bounds in ranges.items():
        invalid = 0
        for row in rows:
            value = row.get(column)
            if value in (None, ""):
                continue
            try:
                number = float(value)
                invalid += not (number >= bounds.get("min", float("-inf")) and number <= bounds.get("max", float("inf")))
            except (TypeError, ValueError):
                invalid += 1
        output.append(_result("numeric_range", invalid == 0, f"{invalid} values outside configured bounds in {column}", dataset, invalid))
    return output


def validate_categories(dataset: str, rows: list[dict[str, Any]], categories: dict[str, list[str]]) -> list[CheckResult]:
    output: list[CheckResult] = []
    for column, allowed in categories.items():
        invalid = sum(row.get(column) not in (None, "") and row.get(column) not in allowed for row in rows)
        output.append(_result("categorical_values", invalid == 0, f"{invalid} values outside configured categories in {column}", dataset, invalid))
    return output


def results_as_dicts(results: list[CheckResult]) -> list[dict[str, Any]]:
    return [asdict(result) for result in results]
