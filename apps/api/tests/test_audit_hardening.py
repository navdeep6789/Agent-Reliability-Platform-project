import pytest
import time
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.storage.database import SessionLocal
from app.storage.models import (
    RunModel, SpanModel, ReliabilityFindingModel, PolicyViolationModel,
    EvaluationRunModel, EvaluationCaseResultModel, ApiKeyModel
)
from app.storage.retention import retention_manager
from app.policies.engine import policy_engine
from app.reliability.engine import reliability_engine
from app.ingestion.normalizer import SpanNormalizer
from arp_schemas import PolicyRuleType, FindingType
from arp.exporter import TelemetryExporter
from arp.observe import Observer

client = TestClient(app)

def test_project_isolation_adversarial():
    """
    Adversarial Project Isolation Test:
    Project Alpha generates a trace and findings.
    Project Beta attempts to read Alpha's trace, waterfall, run, report, and findings.
    Must return 404 / empty results.
    """
    test_uid = f"adv_{int(time.time()*1000)}"
    run_id = f"run_{test_uid}"
    trace_id = f"trace_{test_uid}"
    span_id = f"span_{test_uid}"
    finding_id = f"finding_{test_uid}"

    db = SessionLocal()
    try:
        alpha_run = RunModel(
            run_id=run_id,
            trace_id=trace_id,
            project_id="proj_alpha",
            environment="production",
            agent_name="alpha-bot",
            agent_version="1.0.0",
            status="SUCCESS",
            start_time=datetime.utcnow() - timedelta(minutes=5),
            duration_ms=1200.0,
            total_tokens=500,
            cost_usd=0.005
        )
        db.add(alpha_run)
        
        alpha_span = SpanModel(
            span_id=span_id,
            trace_id=trace_id,
            run_id=run_id,
            name="tool.alpha_secret_tool",
            span_type="tool",
            start_time=datetime.utcnow() - timedelta(minutes=5),
            duration_ms=500.0,
            status="ok",
            attributes_json='{"secret": "alpha_proprietary_data"}'
        )
        db.add(alpha_span)
        
        alpha_finding = ReliabilityFindingModel(
            id=finding_id,
            run_id=run_id,
            trace_id=trace_id,
            project_id="proj_alpha",
            finding_type="TOOL_LATENCY",
            severity="MEDIUM",
            title="Alpha Tool Latency",
            description="Alpha finding",
            details_json='{}',
            suggested_actions_json='[]'
        )
        db.add(alpha_finding)
        db.commit()
    finally:
        db.close()

    # Request from Project Beta
    headers_beta = {"X-Project-Id": "proj_beta"}

    # 1. Beta attempts to get Alpha's trace
    resp = client.get(f"/api/v1/traces/{trace_id}", headers=headers_beta)
    assert resp.status_code == 404

    # 2. Beta attempts to get Alpha's waterfall
    resp = client.get(f"/api/v1/traces/{trace_id}/waterfall", headers=headers_beta)
    assert resp.status_code == 404

    # 3. Beta attempts to get Alpha's run detail
    resp = client.get(f"/api/v1/runs/{run_id}", headers=headers_beta)
    assert resp.status_code == 404

    # 4. Beta attempts to get Alpha's run report
    resp = client.get(f"/api/v1/runs/{run_id}/report", headers=headers_beta)
    assert resp.status_code == 404

    # 5. Beta lists findings - must not contain Alpha finding
    resp = client.get("/api/v1/findings", headers=headers_beta)
    assert resp.status_code == 200
    beta_findings = resp.json()["findings"]
    assert not any(f["id"] == finding_id for f in beta_findings)

def test_data_retention_purge():
    """
    Data Retention Purge Test:
    Creates records older than 30 days and records within 30 days.
    Triggers purge with retention_days=30.
    Verifies expired records are deleted and recent records are preserved.
    """
    test_uid = f"ret_{int(time.time()*1000)}"
    old_run_id = f"run_old_{test_uid}"
    recent_run_id = f"run_recent_{test_uid}"
    proj_id = f"proj_ret_{test_uid}"

    db = SessionLocal()
    old_time = datetime.utcnow() - timedelta(days=45)
    recent_time = datetime.utcnow() - timedelta(days=5)
    
    try:
        # Expired run
        old_run = RunModel(
            run_id=old_run_id,
            trace_id=f"trace_old_{test_uid}",
            project_id=proj_id,
            environment="production",
            agent_name="old-bot",
            agent_version="1.0.0",
            status="SUCCESS",
            start_time=old_time,
            duration_ms=1000.0
        )
        db.add(old_run)
        
        # Recent run
        recent_run = RunModel(
            run_id=recent_run_id,
            trace_id=f"trace_rec_{test_uid}",
            project_id=proj_id,
            environment="production",
            agent_name="recent-bot",
            agent_version="1.0.0",
            status="SUCCESS",
            start_time=recent_time,
            duration_ms=1000.0
        )
        db.add(recent_run)
        db.commit()
    finally:
        db.close()

    # Trigger purge for proj_id
    purge_res = retention_manager.purge_expired_records(retention_days=30, project_id=proj_id)
    assert purge_res["purged_runs"] >= 1

    # Verify old run is gone, recent run remains
    db = SessionLocal()
    try:
        assert db.query(RunModel).filter(RunModel.run_id == old_run_id).first() is None
        assert db.query(RunModel).filter(RunModel.run_id == recent_run_id).first() is not None
    finally:
        db.close()

def test_sdk_fail_open_behavior():
    """
    SDK Failure Test (Fail-Open):
    Simulates a non-existent or down endpoint.
    Agent execution must NOT raise an exception.
    """
    observer = Observer()
    observer.init(
        endpoint="http://127.0.0.1:59999/non_existent_dead_port",
        project_id="proj_fail_open_test",
        fail_closed=False
    )

    try:
        with observer.agent(name="resilient_agent", version="1.0.0") as agent_span:
            with observer.llm(model="gpt-4o") as llm_span:
                observer.record_llm_usage(llm_span, 100, 50)
            with observer.tool(name="calc") as tool_span:
                observer.record_tool_result(tool_span, {"res": 42})
    except Exception as e:
        pytest.fail(f"SDK fail-open failed, raised exception: {e}")

def test_sdk_fail_closed_behavior():
    """
    SDK Failure Test (Fail-Closed):
    When fail_closed=True and queue is full or export fails,
    exception should be raised.
    """
    exporter = TelemetryExporter(
        endpoint="http://127.0.0.1:59999/non_existent_dead_port",
        max_queue_size=1,
        fail_closed=True
    )
    
    # Fill queue
    exporter.enqueue_span({"span_id": "s1"})
    # Enqueue on full queue in fail_closed mode must raise RuntimeError
    with pytest.raises(RuntimeError):
        exporter.enqueue_span({"span_id": "s2"})

def test_policy_engine_exact_boundaries():
    """
    Boundary condition testing for policy engine:
    1. under threshold -> NO violation
    2. exact threshold -> NO violation (for maximums, value == threshold is valid)
    3. over threshold  -> VIOLATION
    """
    # MAX_RUN_LATENCY: threshold = 5.0 seconds
    # Test 1: Under (4.9s = 4900ms)
    v_under = policy_engine.evaluate_run({"run_id": "r1", "duration_ms": 4900.0, "cost_usd": 0.01}, [])
    assert not any(v.rule_type == PolicyRuleType.MAX_RUN_LATENCY for v in v_under)

    # Test 2: Exact (5.0s = 5000ms)
    v_exact = policy_engine.evaluate_run({"run_id": "r2", "duration_ms": 5000.0, "cost_usd": 0.01}, [])
    assert not any(v.rule_type == PolicyRuleType.MAX_RUN_LATENCY for v in v_exact)

    # Test 3: Over (5.01s = 5010ms)
    v_over = policy_engine.evaluate_run({"run_id": "r3", "duration_ms": 5010.0, "cost_usd": 0.01}, [])
    assert any(v.rule_type == PolicyRuleType.MAX_RUN_LATENCY for v in v_over)

    # MAX_RUN_COST: threshold = $0.05
    # Exact ($0.05)
    v_cost_exact = policy_engine.evaluate_run({"run_id": "r4", "duration_ms": 1000.0, "cost_usd": 0.05}, [])
    assert not any(v.rule_type == PolicyRuleType.MAX_RUN_COST for v in v_cost_exact)

    # Over ($0.0501)
    v_cost_over = policy_engine.evaluate_run({"run_id": "r5", "duration_ms": 1000.0, "cost_usd": 0.0501}, [])
    assert any(v.rule_type == PolicyRuleType.MAX_RUN_COST for v in v_cost_over)

    # MIN_EVAL_SCORE: threshold = 0.80
    # Exact (0.80) -> passes
    v_eval_exact = policy_engine.evaluate_run({"run_id": "r6"}, [], eval_score=0.80)
    assert not any(v.rule_type == PolicyRuleType.MIN_EVAL_SCORE for v in v_eval_exact)

    # Under (0.79) -> violation
    v_eval_under = policy_engine.evaluate_run({"run_id": "r7"}, [], eval_score=0.79)
    assert any(v.rule_type == PolicyRuleType.MIN_EVAL_SCORE for v in v_eval_under)

def test_false_positive_prevention_on_healthy_trace():
    """
    False Positive Test:
    Builds a healthy agent trace (single tool call, fast latency, no errors, normal context).
    Asserts ZERO reliability findings are produced.
    """
    run_dict = {
        "run_id": "run_healthy_01",
        "trace_id": "trace_healthy_01",
        "agent_name": "healthy-agent",
        "duration_ms": 1200.0,
        "cost_usd": 0.002,
        "total_tokens": 400,
        "error_count": 0,
        "retry_count": 0
    }
    spans = [
        {
            "span_id": "s_agent",
            "parent_span_id": None,
            "name": "agent.healthy",
            "span_type": "agent",
            "duration_ms": 1200.0,
            "status": "ok",
            "attributes": {}
        },
        {
            "span_id": "s_llm_1",
            "parent_span_id": "s_agent",
            "name": "llm.openai.gpt-4o",
            "span_type": "llm",
            "duration_ms": 400.0,
            "status": "ok",
            "attributes": {"gen_ai.usage.input_tokens": 200, "gen_ai.usage.output_tokens": 50}
        },
        {
            "span_id": "s_tool",
            "parent_span_id": "s_agent",
            "name": "tool.search",
            "span_type": "tool",
            "duration_ms": 250.0, # 250ms is ~20% of trace, not dominating (>30%)
            "status": "ok",
            "attributes": {"arp.tool.name": "search", "arp.tool.retry_count": 0}
        },
        {
            "span_id": "s_llm_2",
            "parent_span_id": "s_agent",
            "name": "llm.openai.gpt-4o",
            "span_type": "llm",
            "duration_ms": 350.0,
            "status": "ok",
            "attributes": {"gen_ai.usage.input_tokens": 250, "gen_ai.usage.output_tokens": 100}
        }
    ]

    report = reliability_engine.analyze_run(run_dict, spans)
    assert len(report.findings) == 0, f"Expected 0 findings on healthy trace, got: {report.findings}"
    assert len(report.retries) == 0
    assert len(report.loops) == 0
    assert report.context_growth is None or not report.context_growth.is_abnormal

def test_span_normalizer_duration_and_attribute_guards():
    """
    Tests that SpanNormalizer:
    1. Clamps negative durations caused by clock skew to 0.0.
    2. Enforces maximum attribute counts and truncates oversized attribute values.
    """
    raw_span = {
        "span_id": "test_clock_skew",
        "trace_id": "trace_skew",
        "name": "skewed_span",
        "duration_ms": -450.0, # negative duration
        "attributes": {
            "huge_string": "A" * 50000, # 50k string (exceeds 16k limit)
            **{f"key_{i}": f"value_{i}" for i in range(200)} # 200 attributes (exceeds 128 max)
        }
    }

    norm = SpanNormalizer.normalize_sdk_span(raw_span)
    assert norm["duration_ms"] >= 0.0
    assert len(norm["attributes"]) <= 128
    assert "huge_string" in norm["attributes"]
    assert len(norm["attributes"]["huge_string"]) < 20000
    assert "... [TRUNCATED]" in norm["attributes"]["huge_string"]

def test_ingestion_payload_batch_limit():
    """
    Ingestion Batch Size Protection:
    Sending a batch greater than 500 spans must return HTTP 413.
    """
    oversized_spans = [{"span_id": f"s_{i}", "name": "span"} for i in range(501)]
    resp = client.post("/api/v1/ingest/spans", json={"spans": oversized_spans})
    assert resp.status_code == 413
