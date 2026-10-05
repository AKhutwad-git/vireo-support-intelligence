from vireo.analytics.economics import calculate_ticket_economics


def _ticket(**kwargs):
    row = {"ticket_id":"t1", "channel":"chat", "customer_id":"c1", "order_id":"o1", "product_sku":"s1",
        "agent_id":"a1", "agent_team":"Team", "agent_tier":"1", "agent_site":"X", "agent_shift":"Day",
        "agent_from_date":"2020-01-01", "agent_to_date":"", "agent_assignment_flag":"matched",
        "attendance_flag":True, "sla_breach_flag":False, "valid_for_sla":True, "sla_status":"met",
        "transfers_numeric":0, "replacement_issued":"N", "refund_amount_inr":"", "refund_reason_code":"",
        "created_at":"2026-01-01T00:00:00+00:00", "resolved_at":"2026-01-01T01:00:00+00:00"}
    return {**row, **kwargs}


def test_cost_components_and_refund_replacement_anomaly():
    products = [{"sku":"s1", "unit_cost_inr":"1000", "family":"headphones", "retail_price_inr":"9999"}]
    rows = calculate_ticket_economics([_ticket(replacement_issued="Y", refund_amount_inr="50", sla_breach_flag=True, transfers_numeric=2)], products, [])
    row = rows[0]
    assert row["contact_cost_inr"] == 210
    assert row["sla_breach_cost_inr"] == 350
    assert row["transfer_cost_inr"] == 610
    assert row["replacement_cost_inr"] == 1340
    assert row["refund_amount_inr"] == 50
    assert row["refund_replacement_anomaly_flag"] is True
    assert row["refund_replacement_anomaly_exposure_inr"] == 1390
    assert row["total_relevant_exposure_inr"] == 2560


def test_missing_unit_cost_is_flagged_not_dropped():
    row = calculate_ticket_economics([_ticket(replacement_issued="Y")], [{"sku":"s1", "unit_cost_inr":""}], [])[0]
    assert row["replacement_cost_missing_flag"] is True
    assert row["replacement_cost_inr"] is None
