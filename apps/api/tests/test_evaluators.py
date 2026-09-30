import pytest
from app.evaluations.evaluators import (
    ExactMatchEvaluator,
    JsonSchemaEvaluator,
    ToolSelectionEvaluator,
    CitationPresenceEvaluator
)

def test_exact_match_evaluator():
    res_pass = ExactMatchEvaluator.evaluate("Order ord_8829 is in transit", "Order ord_8829 is in transit")
    assert res_pass.passed is True
    assert res_pass.score == 1.0

    res_fail = ExactMatchEvaluator.evaluate("Cancelled", "Delivered")
    assert res_fail.passed is False
    assert res_fail.score == 0.0

def test_json_schema_evaluator():
    schema = {
        "type": "object",
        "required": ["order_id", "status", "estimated_delivery"]
    }
    valid_json = '{"order_id": "ord_1", "status": "shipped", "estimated_delivery": "2026-10-01"}'
    res_valid = JsonSchemaEvaluator.evaluate(valid_json, schema)
    assert res_valid.passed is True
    assert res_valid.score == 1.0

    missing_key_json = '{"order_id": "ord_1", "status": "shipped"}'
    res_invalid = JsonSchemaEvaluator.evaluate(missing_key_json, schema)
    assert res_invalid.passed is False
    assert "estimated_delivery" in str(res_invalid.failure_reason)

def test_tool_selection_evaluator():
    expected = ["crm.lookup_customer", "support_kb"]
    called_pass = ["crm.lookup_customer", "support_kb", "extra_logger"]
    res_pass = ToolSelectionEvaluator.evaluate(called_pass, expected)
    assert res_pass.passed is True
    assert res_pass.score == 1.0

    called_fail = ["crm.lookup_customer"]
    res_fail = ToolSelectionEvaluator.evaluate(called_fail, expected)
    assert res_fail.passed is False
    assert res_fail.score == 0.5
    assert "support_kb" in res_fail.details["missing"]

def test_citation_presence_evaluator():
    citations = ["https://arxiv.org/abs/2405.0192", "https://engineering.blog/patterns"]
    text_pass = "According to https://arxiv.org/abs/2405.0192 and https://engineering.blog/patterns..."
    res_pass = CitationPresenceEvaluator.evaluate(text_pass, citations)
    assert res_pass.passed is True

    text_fail = "According to https://arxiv.org/abs/2405.0192 only..."
    res_fail = CitationPresenceEvaluator.evaluate(text_fail, citations)
    assert res_fail.passed is False
    assert res_fail.score == 0.5
