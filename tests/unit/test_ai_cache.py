from vireo.ai.cache import ResultCache, cache_key


def test_identical_input_model_and_prompt_reuse_cache(tmp_path):
    key=cache_key("prompt","model","v1")
    assert key==cache_key("prompt","model","v1")
    assert key!=cache_key("prompt","model2","v1")
    path=tmp_path/"cache.jsonl"; cache=ResultCache(path); cache.set(key,{"theme":"unclear"})
    loaded=ResultCache(path)
    assert loaded.get(key)=={"theme":"unclear"}
    assert "prompt" not in path.read_text(encoding="utf-8")
