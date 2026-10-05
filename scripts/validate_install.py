"""Lightweight installed-package/config and deterministic decision smoke check."""
from pathlib import Path

from vireo import __version__
from vireo.evaluation.synthetic import synthetic_decision_scenarios
from vireo.pipeline.run import load_config


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    config = load_config(ROOT / "configs" / "config.yaml")
    scenarios = synthetic_decision_scenarios(config.get("stage6", {}))
    failures = [row["scenario"] for row in scenarios if row["status"] != "PASS"]
    if failures:
        print(f"Install validation failed for scenarios: {', '.join(failures)}")
        return 1
    print(f"Install validation PASS; version={__version__}; config valid; synthetic decisions={len(scenarios)}; AI calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
