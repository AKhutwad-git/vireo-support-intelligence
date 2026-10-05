"""Explicit hypothetical reduction scenarios against observed exposure."""
from __future__ import annotations

SCENARIO_REDUCTION_RATES = (0.10, 0.20, 0.30)


def opportunity_scenarios(exposures: dict[str, float]) -> list[dict]:
    rows = []
    for driver, exposure in sorted(exposures.items()):
        value = float(exposure)
        if value < 0:
            raise ValueError("observed exposure cannot be negative")
        for rate in SCENARIO_REDUCTION_RATES:
            rows.append({"cost_driver": driver, "scenario_reduction_rate": rate,
                         "observed_exposure_inr": value,
                         "scenario_opportunity_inr": round(value * rate, 2),
                         "scenario_type": "hypothetical_not_realized_savings"})
    return rows
