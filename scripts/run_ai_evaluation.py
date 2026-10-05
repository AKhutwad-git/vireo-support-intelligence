"""Exercise the AI contract with a mock client; this is not model-quality evaluation."""
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from vireo.pipeline.run import load_config, run_pipeline
from vireo.pipeline.ai_analysis import run_stage5_ai


class MockClient:
    provider="mock"
    model="mock-contract-v1"
    def classify_batch(self, requests):
        result=[]
        for req in requests:
            tid=req["ticket_id"]
            result.append({"ticket_id":tid,"result":{"ticket_id":tid,"issue_category":"unclear","secondary_category":"unclear",
                "customer_intent":"unclear","diagnostic_theme":"insufficient_evidence","customer_problem":"unclear",
                "resolution_pattern":"unclear","communication_issue":"unclear","policy_process_issue":"unclear",
                "possible_failure_theme":"unclear","evidence":"","evidence_strength":"insufficient","confidence":0.1},
                "actual_input_tokens":None,"actual_output_tokens":None})
        return result


def main():
    # Rebuild Stages 1–4 before running mock inference against their fresh artifacts.
    pipeline = run_pipeline(ROOT/"configs"/"config.yaml")
    if pipeline.get("status") != "PASS" or pipeline.get("stage4", {}).get("ticket_rows") != 11750:
        print("Deterministic pipeline failed or ticket grain changed; mock Stage 5 not run")
        return 1
    config=load_config(ROOT/"configs"/"config.yaml")
    config["ai"].update({"max_population":3,"top_n":3,"selection_mode":"top_n"})
    with TemporaryDirectory(prefix="vireo-ai-smoke-") as tmp:
        temp_root=Path(tmp)
        interim=temp_root/"interim"
        interim.mkdir()
        for name in ("normalized_tickets", "ticket_metrics", "agent_metrics", "adjusted_agent_metrics",
                     "agent_comparison", "ticket_economics", "agent_economics"):
            shutil.copy2(ROOT/"data"/"interim"/f"{name}.parquet",interim/f"{name}.parquet")
        config["ai"]["cache_path"]=str(temp_root/"cache.jsonl")
        report=run_stage5_ai(interim,config,client=MockClient(),project_root=ROOT)
    print("Deterministic pipeline: Stages 1-4 PASS; ticket grain=11750")
    print(f"Mock contract smoke: selected={report['tickets_selected']}; schema-valid={report['tickets_analyzed']}; model accuracy not measured")
    print(f"Human-reviewed fixture: {report['evaluation']['human_reviewed_sample_size']} labels; no production provider configured")
    return 0 if report["tickets_analyzed"]==report["tickets_selected"] else 1


if __name__=="__main__":
    raise SystemExit(main())
