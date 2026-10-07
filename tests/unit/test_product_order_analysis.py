from vireo.analytics.product_order import build_product_order_analysis, enrich_tickets_with_orders


def _inputs():
    tickets = [
        {"ticket_id": "T1", "order_id": "O1", "customer_id": "C1", "product_sku": "S1", "agent_id": "A1", "attendance_flag": True, "valid_for_csat": True, "csat_score_numeric": 2, "replacement_issued": "Y"},
        {"ticket_id": "T2", "order_id": "", "customer_id": "C2", "product_sku": "S1", "agent_id": "A1", "attendance_flag": True, "valid_for_csat": True, "csat_score_numeric": 4, "replacement_issued": "N"},
        {"ticket_id": "T3", "order_id": "", "customer_id": "C3", "product_sku": "S2", "agent_id": "A2", "attendance_flag": True, "valid_for_csat": False, "csat_score_numeric": None, "replacement_issued": "Y"},
        {"ticket_id": "T4", "order_id": "", "customer_id": "C4", "product_sku": "S3", "agent_id": "A2", "attendance_flag": False, "valid_for_csat": False, "csat_score_numeric": None, "replacement_issued": "N"},
        {"ticket_id": "T5", "order_id": "BAD", "customer_id": "C5", "product_sku": "S4", "agent_id": "A2", "attendance_flag": True, "valid_for_csat": True, "csat_score_numeric": 5, "replacement_issued": "N"},
    ]
    orders = [
        {"order_id": "O1", "customer_id": "C1", "sku": "S1", "channel": "Web", "lot_code": "L1", "qty": "1", "order_value_inr": "100"},
        {"order_id": "O2", "customer_id": "C2", "sku": "S1", "channel": "Market", "lot_code": "L2", "qty": "1", "order_value_inr": "200"},
        {"order_id": "O3", "customer_id": "C3", "sku": "S2", "channel": "Web", "lot_code": "L3", "qty": "1", "order_value_inr": "300"},
        {"order_id": "O4", "customer_id": "C3", "sku": "S2", "channel": "Web", "lot_code": "L4", "qty": "1", "order_value_inr": "300"},
    ]
    products = [{"sku": sku, "product_name": sku, "family": "family", "warranty_months": "12"} for sku in ("S1", "S2", "S3", "S4")]
    economics = [{"ticket_id": ticket["ticket_id"], "replacement_exposure_inr": 500 if ticket["replacement_issued"] == "Y" else 0} for ticket in tickets]
    return tickets, orders, products, economics


def test_order_join_is_one_row_per_ticket_and_classifies_matches():
    tickets, orders, products, economics = _inputs()
    rows = enrich_tickets_with_orders(tickets, orders, products, economics)
    assert len(rows) == len(tickets) == len({row["ticket_id"] for row in rows})
    assert [row["order_match_status"] for row in rows] == ["matched", "matched", "ambiguous", "unmatched", "unmatched"]
    assert rows[0]["order_match_method"] == "direct_order_id"
    assert rows[1]["order_match_method"] == "unique_customer_sku"
    assert rows[2]["order_id"] is None
    assert rows[3]["order_channel"] is None


def test_direct_order_conflict_is_not_silently_reassigned():
    tickets, orders, products, economics = _inputs()
    tickets[0]["customer_id"] = "different-customer"
    rows = enrich_tickets_with_orders(tickets, orders, products, economics)
    assert rows[0]["order_match_status"] == "ambiguous"
    assert rows[0]["order_id"] is None


def test_product_rates_csat_denominators_and_agent_exposure():
    tickets, orders, products, economics = _inputs()
    result = build_product_order_analysis(tickets, orders, products, economics, minimum_support=1)
    summary = result["summary"]
    sku = {row["product_sku"]: row for row in result["product_sku"]}
    assert summary["order_match_counts"] == {"matched": 2, "ambiguous": 1, "unmatched": 2}
    assert summary["rows_before"] == summary["rows_after"] == 5
    assert sku["S1"]["ticket_count"] == 2
    assert sku["S1"]["replacement_eligible_count"] == 2
    assert sku["S1"]["replacement_count"] == 1
    assert sku["S1"]["replacement_rate"] == 0.5
    assert sku["S1"]["replacement_exposure_inr"] == 500
    assert sku["S1"]["csat_response_count"] == 2
    assert sku["S1"]["mean_csat"] == 3
    assert sku["S2"]["csat_response_count"] == 0
    agent = next(row for row in result["agent_product"] if row["agent_id"] == "A1" and row["product_sku"] == "S1")
    assert agent["ticket_count"] == 2
    assert agent["replacement_count"] == 1
    assert agent["share_of_product_tickets"] == 1
    assert agent["share_of_agent_tickets"] == 1
    channels = {row["order_channel"]: row for row in result["order_channel"]}
    assert channels["Web"]["ticket_count"] == 1


def test_ambiguous_direct_key_is_not_fallback_and_min_support_is_explicit():
    tickets, orders, products, economics = _inputs()
    result = build_product_order_analysis(tickets, orders, products, economics, minimum_support=3)
    assert result["summary"]["minimum_support"] == 3
    assert "3" in result["summary"]["minimum_support_definition"]
    assert result["summary"]["lot_status"] == "NOT RELIABLE"
    assert result["lot"] == []
