import logging
from typing import List, Dict, Any, Optional
from arp_schemas import (
    ReliabilityReport,
    ReliabilityFinding,
    FindingType,
    Severity,
    SpanType,
    ToolErrorType
)
from .retry_detector import RetryDetector
from .loop_detector import LoopDetector
from .context_growth import ContextGrowthAnalyzer

logger = logging.getLogger("arp.reliability")

class ReliabilityEngine:
    def __init__(self):
        self.retry_detector = RetryDetector()
        self.loop_detector = LoopDetector(repeat_threshold=3)
        self.context_growth_analyzer = ContextGrowthAnalyzer(growth_threshold_multiplier=2.5)

    def analyze_run(
        self,
        run_dict: Dict[str, Any],
        spans: List[Dict[str, Any]],
        policy_violations: Optional[List[Dict[str, Any]]] = None
    ) -> ReliabilityReport:
        run_id = run_dict.get("run_id", "")
        trace_id = run_dict.get("trace_id", "")
        agent_name = run_dict.get("agent_name", "unknown")
        total_duration = float(run_dict.get("duration_ms") or 0.0)
        if total_duration == 0.0 and spans:
            total_duration = max(float(s.get("duration_ms", 0.0)) for s in spans)

        findings: List[ReliabilityFinding] = []
        investigations: List[str] = []

        # 1. Retry Analysis
        retries, retry_findings = self.retry_detector.analyze(spans, run_id, trace_id)
        findings.extend(retry_findings)

        # 2. Loop Analysis
        loops, loop_findings = self.loop_detector.analyze(spans, run_id, trace_id)
        findings.extend(loop_findings)

        # 3. Context Growth Analysis
        context_growth, context_findings = self.context_growth_analyzer.analyze(spans, run_id, trace_id)
        findings.extend(context_findings)

        # 4. Tool Latency & Contribution Analysis
        tool_spans = [s for s in spans if s.get("span_type") == "tool" or s.get("name", "").startswith("tool.")]
        for tool_span in tool_spans:
            tool_dur = float(tool_span.get("duration_ms", 0.0))
            if total_duration > 0 and tool_dur >= 1000.0:
                contribution_pct = round((tool_dur / total_duration) * 100.0, 1)
                attrs = tool_span.get("attributes", {})
                t_name = attrs.get("arp.tool.name") or tool_span.get("name")

                if contribution_pct >= 30.0:
                    sev = Severity.HIGH if contribution_pct >= 50.0 else Severity.MEDIUM
                    findings.append(ReliabilityFinding(
                        id=f"finding_lat_{run_id}_{tool_span.get('span_id')}",
                        run_id=run_id,
                        trace_id=trace_id,
                        finding_type=FindingType.TOOL_LATENCY,
                        severity=sev,
                        title=f"Tool '{t_name}' dominated trace duration ({contribution_pct}%)",
                        description=(
                            f"The {t_name} tool took {round(tool_dur / 1000.0, 2)}s, "
                            f"accounting for {contribution_pct}% of the total run latency ({round(total_duration / 1000.0, 2)}s)."
                        ),
                        target_entity=t_name,
                        observed_metric=f"{round(tool_dur / 1000.0, 2)}s ({contribution_pct}%)",
                        trace_contribution_percent=contribution_pct,
                        details={
                            "tool_duration_ms": tool_dur,
                            "total_duration_ms": total_duration,
                            "contribution_percent": contribution_pct,
                            "span_id": tool_span.get("span_id")
                        },
                        suggested_actions=[
                            f"Examine backend performance and indexing for {t_name}",
                            "Evaluate if tool queries can be parallelized or cached",
                            "Consider setting a tighter execution timeout"
                        ]
                    ))
                    investigations.append(f"Investigate high latency in {t_name} ({contribution_pct}% contribution)")

        # 5. Failed Tool Calls & Error Taxonomy
        for s in spans:
            if s.get("status") == "error":
                attrs = s.get("attributes", {})
                span_type = s.get("span_type")
                name = s.get("name")
                err_type = attrs.get("arp.tool.error_type") or "application_error"
                status_msg = s.get("status_message") or "Unknown error"

                if span_type == "tool":
                    f_type = FindingType.TOOL_VALIDATION_ERROR if err_type == "validation_error" else FindingType.FAILED_TOOL
                    sev = Severity.HIGH if err_type in ("timeout", "unavailable") else Severity.MEDIUM
                    findings.append(ReliabilityFinding(
                        id=f"finding_fail_{run_id}_{s.get('span_id')}",
                        run_id=run_id,
                        trace_id=trace_id,
                        finding_type=f_type,
                        severity=sev,
                        title=f"Tool failure in '{name}' ({err_type})",
                        description=f"Tool call failed with {err_type}: {status_msg}",
                        target_entity=name,
                        observed_metric=err_type,
                        details={"error_type": err_type, "message": status_msg, "span_id": s.get("span_id")},
                        suggested_actions=[
                            "Check tool input arguments against expected schema",
                            "Review target service logs and availability"
                        ]
                    ))
                    investigations.append(f"Resolve tool failure on {name}: {err_type}")

                elif span_type == "llm":
                    findings.append(ReliabilityFinding(
                        id=f"finding_llm_fail_{run_id}_{s.get('span_id')}",
                        run_id=run_id,
                        trace_id=trace_id,
                        finding_type=FindingType.PROVIDER_FAILURE,
                        severity=Severity.CRITICAL,
                        title=f"LLM Provider failure on '{name}'",
                        description=f"Model call failed: {status_msg}",
                        target_entity=name,
                        observed_metric="model_error",
                        details={"message": status_msg, "span_id": s.get("span_id")},
                        suggested_actions=[
                            "Implement fallback to secondary model provider (e.g. Anthropic/Google)",
                            "Check provider rate limits and status page"
                        ]
                    ))
                    investigations.append(f"Model provider outage/error for {name}")

        # 6. Missing Telemetry Detection
        known_span_ids = {s.get("span_id") for s in spans}
        for s in spans:
            p_id = s.get("parent_span_id")
            if p_id and p_id not in known_span_ids:
                findings.append(ReliabilityFinding(
                    id=f"finding_missing_telemetry_{run_id}_{s.get('span_id')}",
                    run_id=run_id,
                    trace_id=trace_id,
                    finding_type=FindingType.MISSING_TELEMETRY,
                    severity=Severity.LOW,
                    title="Missing parent span in trace",
                    description=f"Span '{s.get('name')}' references parent '{p_id}', which was not captured or was dropped.",
                    target_entity=s.get("name"),
                    observed_metric="orphan_span",
                    details={"span_id": s.get("span_id"), "missing_parent_id": p_id},
                    suggested_actions=[
                        "Verify context propagation between asynchronous tasks or worker boundaries",
                        "Check exporter queue limits for dropped spans"
                    ]
                ))
                break

        # 7. Collect generic investigations if empty
        if not investigations and findings:
            for f in findings:
                investigations.extend(f.suggested_actions[:1])

        return ReliabilityReport(
            run_id=run_id,
            trace_id=trace_id,
            agent_name=agent_name,
            total_duration_ms=total_duration,
            total_cost_usd=run_dict.get("cost_usd"),
            total_tokens=int(run_dict.get("total_tokens") or 0),
            error_count=int(run_dict.get("error_count") or 0),
            retry_count=int(run_dict.get("retry_count") or 0),
            findings=findings,
            retries=retries,
            context_growth=context_growth,
            loops=loops,
            policy_violations=policy_violations or [],
            suggested_investigations=list(set(investigations))
        )

# Global reliability engine instance
reliability_engine = ReliabilityEngine()
