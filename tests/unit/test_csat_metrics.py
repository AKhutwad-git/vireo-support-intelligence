from vireo.analytics.csat import csat_eligibility, csat_summary

def test_blank_excluded_valid_1_to_5_included_and_rate_denominator():
    rows = [{"status":"resolved", "attendance_flag":True, "csat_score":""},
            {"status":"closed", "attendance_flag":True, "csat_score":"5"},
            {"status":"resolved", "attendance_flag":True, "csat_score":"1"}]
    valid = []
    for row in rows:
        ok, score, reason = csat_eligibility(row)
        row.update(valid_for_csat=ok and row["attendance_flag"], csat_response_flag=ok, csat_score_numeric=score, csat_eligibility_reason=reason)
        if ok: valid.append(score)
    result = csat_summary(rows)
    assert result["csat_response_count"] == 2
    assert result["csat_response_rate"] == 2 / 3
    assert result["mean_csat"] == 3
    assert result["csat_score_1_count"] == result["csat_score_5_count"] == 1

def test_empty_csat_population_is_undefined_not_zero():
    result = csat_summary([{"attendance_flag":True, "valid_for_csat":False}])
    assert result["csat_response_count"] == 0
    assert result["mean_csat"] is None
    assert result["csat_response_rate"] == 0

def test_populated_score_on_open_ticket_is_retained_and_flaggable():
    row = {"status":"open", "attendance_flag":False, "csat_score":"4"}
    ok, score, reason = csat_eligibility(row)
    row.update(valid_for_csat=ok and row["attendance_flag"], csat_response_flag=ok, csat_score_numeric=score, csat_eligibility_reason=reason,
               csat_unexpected_status_flag=True)
    result = csat_summary([row, {"attendance_flag":True, "valid_for_csat":False}])
    assert result["csat_response_count"] == 0
    assert result["csat_populated_valid_score_count"] == 1
    assert result["mean_csat"] is None
    assert result["csat_response_on_noncompleted_count"] == 1
