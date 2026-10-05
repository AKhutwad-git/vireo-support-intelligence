from vireo.analytics.repeat_contacts import detect_repeat_contacts


def _row(tid, created, resolved=None, customer="c", order="o", sku="s"):
    return {"ticket_id":tid, "created_at":created, "resolved_at":resolved, "customer_id":customer, "order_id":order, "product_sku":sku}


def test_same_customer_order_within_30_days():
    rows = detect_repeat_contacts([_row("a","2026-01-01T00:00:00+00:00","2026-01-01T01:00:00+00:00"), _row("b","2026-01-10T00:00:00+00:00")])
    assert rows[1]["repeat_contact_candidate_flag"]
    assert rows[1]["repeat_contact_match_method"] == "customer_order_id"


def test_product_fallback_and_missing_product():
    rows = detect_repeat_contacts([_row("a","2026-01-01T00:00:00+00:00","2026-01-01T01:00:00+00:00",order="",sku="s"),
        _row("b","2026-01-10T00:00:00+00:00",order="",sku="s"), _row("c","2026-01-11T00:00:00+00:00",order="",sku="")])
    assert rows[1]["repeat_contact_match_method"] == "customer_product_sku_fallback"
    assert rows[2]["repeat_contact_candidate_flag"] is False


def test_outside_window_and_unrelated_customer_not_matches():
    rows = detect_repeat_contacts([_row("a","2026-01-01T00:00:00+00:00","2026-01-01T01:00:00+00:00"),
        _row("b","2026-02-02T01:00:00+00:00"), _row("c","2026-01-10T00:00:00+00:00",customer="else")])
    assert not rows[1]["repeat_contact_candidate_flag"]
    assert not rows[2]["repeat_contact_candidate_flag"]
