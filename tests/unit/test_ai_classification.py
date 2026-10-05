from vireo.ai.cache import ResultCache
from vireo.ai.classification import analyze_batch
from vireo.ai.client import OpenAICompatibleClient
import json


VALID={"issue_category":"other","secondary_category":"unclear","customer_intent":"other","diagnostic_theme":"no_recurring_theme",
"customer_problem":"unclear","resolution_pattern":"unclear","communication_issue":"unclear","policy_process_issue":"unclear",
"possible_failure_theme":"unclear","evidence":"help me","evidence_strength":"moderate","confidence":0.5}


class Fake:
    model="fake-v1"; provider="mock"
    def __init__(self,result): self.result=result; self.calls=0
    def classify_batch(self,items):
        self.calls+=1
        return [{"ticket_id":x["ticket_id"],"result":{"ticket_id":x["ticket_id"],**self.result}} for x in items]


class Broken:
    def classify_batch(self,items): raise TimeoutError("provider timeout")


def _row():
    return {"ticket_id":"t1","channel":"chat","priority":"Normal","category":"Other","valid_for_csat":False,
        "valid_for_handle_time":False,"sla_status":"unknown","transfers_numeric":0,"refund_amount_inr":0,
        "replacement_issued_flag":False,"analysis_customer_text":"help me","analysis_agent_notes":""}


def test_mock_structured_classification_and_uncertain_output(tmp_path):
    client=Fake(VALID); cache=ResultCache(tmp_path/"cache.jsonl")
    result,errors,cached=analyze_batch([_row()],client,"id={ticket_id}; {customer_message}","v1","fake-v1",cache)
    assert not errors and result["t1"]["result"]["issue_category"]=="other" and cached==0
    uncertain={**VALID,"issue_category":"insufficient_evidence","evidence":"","evidence_strength":"insufficient","confidence":0.2}
    out,errors,_=analyze_batch([_row()],Fake(uncertain),"id={ticket_id}; {customer_message}","v1","fake-v1",ResultCache(tmp_path/"other.jsonl"))
    assert not errors and out["t1"]["result"]["issue_category"]=="insufficient_evidence"


def test_malformed_output_fails_safely(tmp_path):
    out,errors,_=analyze_batch([_row()],Fake({"issue_category":"made_up"}),"{ticket_id}","v1","fake",ResultCache(tmp_path/"cache"))
    assert not out and errors["t1"].startswith("invalid_model_output")


def test_cache_prevents_duplicate_provider_call_and_provider_failure_isolated(tmp_path):
    client=Fake(VALID); cache=ResultCache(tmp_path/"cache.jsonl")
    first,_,_=analyze_batch([_row()],client,"id={ticket_id}; {customer_message}","v1","fake-v1",cache)
    second,errors,cached=analyze_batch([_row()],client,"id={ticket_id}; {customer_message}","v1","fake-v1",cache)
    assert client.calls==1 and cached==1 and second["t1"]["status"]=="cached" and not errors
    failed,errors,_=analyze_batch([_row()],Broken(),"id={ticket_id}; {customer_message}","v1","broken",ResultCache(tmp_path/"failed"))
    assert not failed and errors["t1"]=="provider_error:TimeoutError"


def test_per_ticket_provider_error_does_not_block_other_results_or_cache_failure(tmp_path):
    class Partial:
        def classify_batch(self, items):
            return [{"ticket_id":items[0]["ticket_id"],"error":"TimeoutError"},
                    {"ticket_id":items[1]["ticket_id"],"result":{"ticket_id":items[1]["ticket_id"],**VALID}}]
    class CacheWriteFails:
        @staticmethod
        def make_key(*args): return "key"
        @staticmethod
        def get(_key): return None
        @staticmethod
        def set(_key,_value): raise OSError("disk full")
    rows=[_row(),{**_row(),"ticket_id":"t2"}]
    outputs,errors,_=analyze_batch(rows,Partial(),"id={ticket_id}; {customer_message}","v1","fake",CacheWriteFails())
    assert errors=={"t1":"provider_error:TimeoutError"}
    assert outputs["t2"]["result"]["issue_category"]=="other"


def test_http_client_keeps_later_ticket_after_one_request_fails(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self,*_args): return False
        def read(self):
            result={"ticket_id":"t2",**VALID}
            body={"usage":{},"choices":[{"message":{"content":json.dumps(result)} }]}
            return json.dumps(body).encode()
    calls=iter([TimeoutError("first ticket timeout"),Response()])
    def fake_urlopen(*_args,**_kwargs):
        value=next(calls)
        if isinstance(value,Exception): raise value
        return value
    monkeypatch.setenv("TEST_AI_KEY","configured")
    monkeypatch.setattr("vireo.ai.client.urlopen",fake_urlopen)
    client=OpenAICompatibleClient("https://unused.invalid","test-model","TEST_AI_KEY")
    results=client.classify_batch([{"ticket_id":"t1","prompt":"one"},{"ticket_id":"t2","prompt":"two"}])
    assert results[0]=={"ticket_id":"t1","error":"TimeoutError"}
    assert results[1]["ticket_id"]=="t2" and results[1]["result"]["issue_category"]=="other"
