from vireo.ai.cost import estimate_cost, estimate_tokens
from vireo.ai.evaluation import score_classification


def test_token_proxy_and_configured_cost_math():
    assert estimate_tokens("abcd") == 1
    assert estimate_cost(1_000_000,500_000,{"input_per_million_usd":2,"output_per_million_usd":4})==4
    assert estimate_cost(100,100,{"input_per_million_usd":None,"output_per_million_usd":None}) is None


def test_reviewed_classification_metrics_are_computed_correctly():
    metrics=score_classification({"a":"x","b":"x","c":"y"},{"a":"x","b":"y","c":"y"})
    assert metrics["sample_size"]==3 and metrics["accuracy"]==2/3
    assert 0 <= metrics["macro_f1"] <= 1
