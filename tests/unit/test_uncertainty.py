from vireo.analytics.uncertainty import mean_interval, standardized_gap_interval, evidence_label

def test_sample_size_and_tiny_sample_uncertainty():
    tiny=mean_interval([4])
    large=mean_interval([3,4,3,4,3,4,3,4])
    assert tiny["sample_size"]==1 and tiny["standard_error"] is None
    assert large["sample_size"]==8 and large["standard_error"] is not None
    assert large["ci_lower"]<=large["mean"]<=large["ci_upper"]
    assert evidence_label(5).startswith("limited")
    assert evidence_label(100).startswith("30+")

def test_standardized_gap_uncertainty_bounds():
    result=standardized_gap_interval([4,5,4,5],[[3,4,3,4],[3,4,3,4],[3,4,3,4],[3,4,3,4]],gap_bounds=(-4,4))
    assert result["sample_size"]==4
    assert -4<=result["ci_lower"]<=result["ci_upper"]<=4
