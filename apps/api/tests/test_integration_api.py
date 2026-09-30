import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_e2e_pipeline():
    # 1. Ingest a multi-span agent run
    trace_id = "test_e2e_trace_999"
    run_id = "test_e2e_run_999"
    
    payload = {
        "spans": [
            {
                "span_id": "span_root",
                "trace_id": trace_id,
                "run_id": run_id,
                "parent_span_id": None,
                "name": "agent.support",
                "span_type": "agent",
                "start_time": "2026-09-30T02:00:00.000",
                "end_time": "2026-09-30T02:00:03.000",
                "duration_ms": 3000.0,
                "status": "ok",
                "attributes": {
                    "arp.agent.name": "support_bot",
                    "arp.agent.version": "1.0.0"
                }
            },
            {
                "span_id": "span_crm_slow",
                "trace_id": trace_id,
                "run_id": run_id,
                "parent_span_id": "span_root",
                "name": "tool.crm_lookup",
                "span_type": "tool",
                "start_time": "2026-09-30T02:00:00.500",
                "end_time": "2026-09-30T02:00:02.500",
                "duration_ms": 2000.0, # 2000ms / 3000ms = 66.7% contribution!
                "status": "ok",
                "attributes": {
                    "arp.tool.name": "crm_lookup",
                    "arp.tool.status": "ok"
                }
            },
            {
                "span_id": "span_llm",
                "trace_id": trace_id,
                "run_id": run_id,
                "parent_span_id": "span_root",
                "name": "llm.gpt-4o",
                "span_type": "llm",
                "start_time": "2026-09-30T02:00:02.500",
                "end_time": "2026-09-30T02:00:02.900",
                "duration_ms": 400.0,
                "status": "ok",
                "attributes": {
                    "gen_ai.system": "openai",
                    "gen_ai.request.model": "gpt-4o",
                    "gen_ai.usage.input_tokens": 1200,
                    "gen_ai.usage.output_tokens": 250
                }
            }
        ]
    }

    # Ingest
    res_ingest = client.post("/api/v1/ingest/spans", json=payload)
    assert res_ingest.status_code == 200
    assert res_ingest.json()["spans_processed"] == 3

    # 2. Query trace
    res_trace = client.get(f"/api/v1/traces/{trace_id}")
    assert res_trace.status_code == 200
    trace_data = res_trace.json()
    assert trace_data["trace_id"] == trace_id
    assert len(trace_data["spans"]) == 3

    # 3. Query waterfall
    res_waterfall = client.get(f"/api/v1/traces/{trace_id}/waterfall")
    assert res_waterfall.status_code == 200
    wf_data = res_waterfall.json()
    assert wf_data["trace_id"] == trace_id
    assert len(wf_data["root_spans"]) == 1
    root = wf_data["root_spans"][0]
    assert len(root["children"]) == 2

    # 4. Query run and report
    res_report = client.get(f"/api/v1/runs/{run_id}/report")
    assert res_report.status_code == 200
    report_data = res_report.json()
    assert report_data["run_id"] == run_id
    # Tool latency finding should be present for CRM tool (66.7% of trace duration)
    assert any(f["finding_type"] == "TOOL_LATENCY" for f in report_data["findings"])

    # 5. Query Agents list
    res_agents = client.get("/api/v1/agents")
    assert res_agents.status_code == 200
    assert any(a["name"] == "support_bot" for a in res_agents.json()["agents"])
