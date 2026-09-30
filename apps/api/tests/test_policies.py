import pytest
from app.policies.engine import PolicyEngine
from arp_schemas import PolicyRuleType

def test_policy_engine_max_latency_violation():
    engine = PolicyEngine()
    run_dict = {
        "run_id": "run_slow",
        "trace_id": "trace_slow",
        "duration_ms": 6200.0, # 6.2s > 5.0s threshold
        "cost_usd": 0.01,
        "retry_count": 0
    }
    violations = engine.evaluate_run(run_dict, [])
    assert any(v.rule_type == PolicyRuleType.MAX_RUN_LATENCY for v in violations)

def test_policy_engine_max_cost_violation():
    engine = PolicyEngine()
    run_dict = {
        "run_id": "run_expensive",
        "trace_id": "trace_expensive",
        "duration_ms": 2000.0,
        "cost_usd": 0.082, # $0.082 > $0.05 limit
        "retry_count": 0
    }
    violations = engine.evaluate_run(run_dict, [])
    assert any(v.rule_type == PolicyRuleType.MAX_RUN_COST for v in violations)

def test_policy_engine_max_retries_violation():
    engine = PolicyEngine()
    run_dict = {
        "run_id": "run_retry_storm",
        "trace_id": "trace_retry_storm",
        "duration_ms": 2000.0,
        "cost_usd": 0.01,
        "retry_count": 3 # 3 > 2 limit
    }
    violations = engine.evaluate_run(run_dict, [])
    assert any(v.rule_type == PolicyRuleType.MAX_TOOL_RETRIES for v in violations)
