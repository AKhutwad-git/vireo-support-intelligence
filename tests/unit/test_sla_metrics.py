from vireo.analytics.sla import DEFAULT_SLA_TARGETS, sla_for_ticket, sla_summary

def test_policy_targets():
    assert DEFAULT_SLA_TARGETS == {"chat":15,"voice":120,"social":240,"email":480}

def test_on_target_before_after_missing_and_unknown():
    base = {"created_at":"2025-01-01T00:00:00+00:00", "channel":"chat"}
    def at(minutes, **extra):
        from datetime import datetime, timedelta, timezone
        t = datetime(2025,1,1,tzinfo=timezone.utc) + timedelta(minutes=minutes)
        return sla_for_ticket({**base, "first_response_at":t.isoformat(), **extra})
    assert at(15)["sla_status"] == "met"
    assert at(14.9)["sla_status"] == "met"
    assert at(15.1)["sla_status"] == "breached"
    assert sla_for_ticket({**base,"first_response_at":None})["sla_status"] == "not_evaluable"
    assert sla_for_ticket({**base,"channel":"fax","first_response_at":"2025-01-01T00:01:00+00:00"})["sla_eligibility_reason"] == "unknown_channel"

def test_each_channel_target_is_met_at_boundary_and_breached_after():
    from datetime import datetime, timedelta, timezone
    for channel, target in DEFAULT_SLA_TARGETS.items():
        for minutes, expected in ((target, "met"), (target + .01, "breached")):
            response = (datetime(2025,1,1,tzinfo=timezone.utc)+timedelta(minutes=minutes)).isoformat()
            result = sla_for_ticket({"channel":channel,"created_at":"2025-01-01T00:00:00+00:00","first_response_at":response})
            assert result["sla_status"] == expected

def test_summary_rate_denominator():
    result = sla_summary([{"sla_status":"met"},{"sla_status":"breached"},{"sla_status":"not_evaluable"}])
    assert result["sla_eligible_count"] == 2
    assert result["sla_breach_rate"] == .5
