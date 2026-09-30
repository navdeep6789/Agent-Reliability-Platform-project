import pytest
from app.reliability.retry_detector import RetryDetector
from app.reliability.loop_detector import LoopDetector
from app.reliability.context_growth import ContextGrowthAnalyzer
from arp_schemas import FindingType, Severity

def test_retry_detector():
    detector = RetryDetector()
    spans = [
        {
            "span_id": "s1", "name": "tool.crm", "span_type": "tool",
            "start_time": "2026-09-30T01:00:00", "duration_ms": 300.0,
            "status": "error", "status_message": "Gateway timeout", "attributes": {"arp.tool.name": "crm"}
        },
        {
            "span_id": "s2", "name": "tool.crm", "span_type": "tool",
            "start_time": "2026-09-30T01:00:01", "duration_ms": 350.0,
            "status": "error", "status_message": "Gateway timeout", "attributes": {"arp.tool.name": "crm"}
        },
        {
            "span_id": "s3", "name": "tool.crm", "span_type": "tool",
            "start_time": "2026-09-30T01:00:02", "duration_ms": 200.0,
            "status": "ok", "attributes": {"arp.tool.name": "crm"}
        }
    ]
    analyses, findings = detector.analyze(spans, "run_test_1", "trace_test_1")
    assert len(analyses) == 1
    assert analyses[0].total_retries == 2
    assert analyses[0].final_status == "SUCCESS"
    assert len(findings) == 1
    assert findings[0].finding_type in (FindingType.RETRY_LOOP, FindingType.RETRY_STORM)

def test_loop_detector_repeated_calls():
    detector = LoopDetector(repeat_threshold=3)
    spans = [
        {"name": "tool.search", "span_type": "tool", "start_time": "2026-09-30T01:00:01", "duration_ms": 100.0},
        {"name": "tool.search", "span_type": "tool", "start_time": "2026-09-30T01:00:02", "duration_ms": 100.0},
        {"name": "tool.search", "span_type": "tool", "start_time": "2026-09-30T01:00:03", "duration_ms": 100.0},
        {"name": "tool.search", "span_type": "tool", "start_time": "2026-09-30T01:00:04", "duration_ms": 100.0}
    ]
    analyses, findings = detector.analyze(spans, "run_test_2", "trace_test_2")
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.REPEATED_SEQUENCE
    assert findings[0].target_entity == "tool.search"

def test_context_growth_analyzer():
    analyzer = ContextGrowthAnalyzer(growth_threshold_multiplier=2.5)
    spans = [
        {
            "span_id": "llm_1", "name": "llm.gpt-4o", "span_type": "llm",
            "start_time": "2026-09-30T01:00:01",
            "attributes": {"gen_ai.usage.input_tokens": 2400, "gen_ai.usage.output_tokens": 300}
        },
        {
            "span_id": "llm_2", "name": "llm.gpt-4o", "span_type": "llm",
            "start_time": "2026-09-30T01:00:02",
            "attributes": {"gen_ai.usage.input_tokens": 5900, "gen_ai.usage.output_tokens": 400}
        },
        {
            "span_id": "llm_3", "name": "llm.gpt-4o", "span_type": "llm",
            "start_time": "2026-09-30T01:00:03",
            "attributes": {"gen_ai.usage.input_tokens": 14200, "gen_ai.usage.output_tokens": 600}
        },
        {
            "span_id": "llm_4", "name": "llm.gpt-4o", "span_type": "llm",
            "start_time": "2026-09-30T01:00:04",
            "attributes": {"gen_ai.usage.input_tokens": 31800, "gen_ai.usage.output_tokens": 900}
        }
    ]
    analysis, findings = analyzer.analyze(spans, "run_test_3", "trace_test_3")
    assert analysis is not None
    assert analysis.growth_multiplier >= 13.0
    assert analysis.is_abnormal is True
    assert len(findings) == 1
    assert findings[0].finding_type == FindingType.CONTEXT_GROWTH
