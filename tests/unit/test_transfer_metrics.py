from vireo.analytics.transfers import transfer_value, transfer_summary

def test_transfer_values_and_rates():
    vals = [transfer_value(x) for x in ("0","1","3")]
    rows = [{"transfers_numeric":v,"valid_for_transfers":True,"attendance_flag":True} for v,_ in vals]
    result = transfer_summary(rows)
    assert result["total_transfers"] == 4
    assert result["transferred_ticket_count"] == 2
    assert result["transfer_rate"] == 2/3
    assert result["transfers_per_completed_ticket"] == 4/3

def test_missing_and_invalid_transfer_values_are_ineligible():
    assert transfer_value("") == (None,"missing")
    assert transfer_value("x") == (None,"invalid")
    assert transfer_value("-1") == (None,"negative")
