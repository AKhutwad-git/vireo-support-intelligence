from vireo.analytics.attendance import attendance_flag, attendance_summary

def test_completed_statuses_and_summary():
    statuses = ["resolved","closed","open","pending"]
    assert [attendance_flag(x) for x in statuses] == [True,True,False,False]
    result = attendance_summary([{"status":x} for x in statuses])
    assert result["completed_ticket_count"] == 2
    assert result["resolved_ticket_count"] == result["closed_ticket_count"] == 1
    assert result["open_pending_ticket_count"] == 2
