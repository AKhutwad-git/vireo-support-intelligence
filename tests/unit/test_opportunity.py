from vireo.analytics.opportunity import opportunity_scenarios


def test_10_20_30_percent_scenarios():
    rows = opportunity_scenarios({"sla":3500})
    assert [r["scenario_opportunity_inr"] for r in rows] == [350,700,1050]
    assert all(r["scenario_opportunity_inr"] <= r["observed_exposure_inr"] for r in rows)
    assert all(r["scenario_type"] == "hypothetical_not_realized_savings" for r in rows)
