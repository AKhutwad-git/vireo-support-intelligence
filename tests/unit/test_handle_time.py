from vireo.analytics.handle_time import elapsed_minutes, percentile

def test_handle_time_uses_first_response_to_resolution():
    assert elapsed_minutes("2025-01-01T00:10:00+00:00", "2025-01-01T01:10:00+00:00") == (60, "")

def test_missing_invalid_negative_and_boundary_durations():
    assert elapsed_minutes(None, "2025-01-01T00:00:00+00:00")[1] == "missing_timestamp"
    assert elapsed_minutes("2025-01-01T00:00:00+00:00", None)[1] == "missing_timestamp"
    assert elapsed_minutes("bad", "2025-01-01T00:00:00+00:00")[1] == "invalid_timestamp"
    assert elapsed_minutes("2025-01-02T00:00:00+00:00", "2025-01-01T00:00:00+00:00")[1] == "negative_duration"
    assert elapsed_minutes("2025-01-01T00:00:00+00:00", "2025-01-01T00:00:00+00:00")[0] == 0

def test_percentile_interpolation_and_empty():
    assert percentile([0, 10], .75) == 7.5
    assert percentile([], .5) is None
