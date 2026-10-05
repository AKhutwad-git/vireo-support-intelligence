from vireo.analytics.case_mix import add_product_family, case_mix_metrics

def test_mix_distributions_sum_and_missing_levels_are_explicit():
    rows=[{"agent_id":"a","agent_assignment_flag":"matched","agent_team":"T","agent_tier":"1","agent_site":"P","agent_shift":"D","agent_from_date":"2025-01-01","agent_to_date":"","channel":"chat","priority":"High","category":None,"product_sku":"x","reporting_month":"2025-01","reporting_quarter":"2025-Q1"},
          {"agent_id":"a","agent_assignment_flag":"matched","agent_team":"T","agent_tier":"1","agent_site":"P","agent_shift":"D","agent_from_date":"2025-01-01","agent_to_date":"","channel":"email","priority":"Normal","category":"Billing","product_sku":"x","reporting_month":"2025-01","reporting_quarter":"2025-Q1"}]
    rows=add_product_family(rows,[{"sku":"x","family":"Audio"}])
    mix=case_mix_metrics(rows)
    full=[r for r in mix if r["period_type"]=="full_available_period"]
    for dimension in {r["dimension"] for r in full}:
        assert abs(sum(r["share"] for r in full if r["dimension"]==dimension)-1)<1e-9
    assert any(r["dimension"]=="category" and r["missing_level_flag"] and r["level"]=="(missing)" for r in full)
    assert {r["level"] for r in full if r["dimension"]=="product_family"}=={"Audio"}
