from typing import List, Dict, Any, Tuple
from arp_schemas import (
    Span, ReliabilityFinding, FindingType, Severity, RetryAnalysis, RetryStep
)

class RetryDetector:
    def analyze(self, spans: List[Dict[str, Any]], run_id: str, trace_id: str) -> Tuple[List[RetryAnalysis], List[ReliabilityFinding]]:
        tool_spans = [s for s in spans if s.get("span_type") == "tool" or s.get("name", "").startswith("tool.")]
        # Sort by start_time
        tool_spans.sort(key=lambda x: str(x.get("start_time", "")))

        # Group by tool name
        tool_sequences: Dict[str, List[Dict[str, Any]]] = {}
        for s in tool_spans:
            attrs = s.get("attributes", {})
            name = attrs.get("arp.tool.name") or s.get("name", "unknown_tool")
            tool_sequences.setdefault(name, []).append(s)

        analyses: List[RetryAnalysis] = []
        findings: List[ReliabilityFinding] = []

        for tool_name, calls in tool_sequences.items():
            if len(calls) < 2:
                # Check single call with explicit retry count attribute
                s = calls[0]
                attrs = s.get("attributes", {})
                retry_count = int(attrs.get("arp.tool.retry_count") or 0)
                if retry_count > 0:
                    status = "SUCCESS" if s.get("status") == "ok" else "FAILED"
                    err_msg = s.get("status_message") or attrs.get("arp.tool.error_type")
                    analysis = RetryAnalysis(
                        tool_name=tool_name,
                        total_retries=retry_count,
                        total_retry_latency_ms=float(s.get("duration_ms", 0.0)),
                        final_status=status,
                        retry_reasons=[str(err_msg)] if err_msg else ["transient_error"],
                        steps=[
                            RetryStep(
                                attempt=retry_count + 1,
                                span_id=s.get("span_id", ""),
                                duration_ms=float(s.get("duration_ms", 0.0)),
                                status=status,
                                error_message=err_msg
                            )
                        ]
                    )
                    analyses.append(analysis)
                    severity = Severity.HIGH if retry_count >= 3 else Severity.MEDIUM
                    findings.append(ReliabilityFinding(
                        id=f"finding_retry_{run_id}_{tool_name}",
                        run_id=run_id,
                        trace_id=trace_id,
                        finding_type=FindingType.RETRY_STORM if retry_count >= 3 else FindingType.RETRY_LOOP,
                        severity=severity,
                        title=f"Retry detected on tool '{tool_name}'",
                        description=f"Tool '{tool_name}' was retried {retry_count} times before reaching {status}.",
                        target_entity=tool_name,
                        observed_metric=f"{retry_count} retries",
                        details={"total_retries": retry_count, "final_status": status},
                        suggested_actions=[
                            f"Check network stability and timeout settings for {tool_name}",
                            "Implement exponential backoff or circuit breaker to prevent retry storms"
                        ]
                    ))
                continue

            # Check consecutive calls indicating retry
            steps: List[RetryStep] = []
            reasons = []
            total_retry_latency = 0.0
            error_count = 0

            for idx, call in enumerate(calls):
                attrs = call.get("attributes", {})
                c_status = call.get("status", "ok")
                err_msg = call.get("status_message") or attrs.get("arp.tool.error_type")
                dur = float(call.get("duration_ms", 0.0))
                total_retry_latency += dur

                if c_status != "ok":
                    error_count += 1
                    if err_msg:
                        reasons.append(str(err_msg))

                steps.append(RetryStep(
                    attempt=idx + 1,
                    span_id=call.get("span_id", ""),
                    duration_ms=dur,
                    status="SUCCESS" if c_status == "ok" else "FAILED",
                    error_message=err_msg
                ))

            if error_count > 0:
                final_status = "SUCCESS" if calls[-1].get("status") == "ok" else "FAILED"
                retry_count = len(calls) - 1
                analysis = RetryAnalysis(
                    tool_name=tool_name,
                    total_retries=retry_count,
                    total_retry_latency_ms=round(total_retry_latency, 2),
                    final_status=final_status,
                    retry_reasons=list(set(reasons)),
                    steps=steps
                )
                analyses.append(analysis)

                is_storm = retry_count >= 3
                severity = Severity.HIGH if is_storm else Severity.MEDIUM
                findings.append(ReliabilityFinding(
                    id=f"finding_retry_{run_id}_{tool_name}",
                    run_id=run_id,
                    trace_id=trace_id,
                    finding_type=FindingType.RETRY_STORM if is_storm else FindingType.RETRY_LOOP,
                    severity=severity,
                    title=f"{'Retry storm' if is_storm else 'Repeated retries'} on tool '{tool_name}'",
                    description=(
                        f"The run retried tool '{tool_name}' {retry_count} times before {final_status.lower()}. "
                        f"Total retry latency accounted for {round(total_retry_latency / 1000.0, 2)}s."
                    ),
                    target_entity=tool_name,
                    observed_metric=f"{retry_count} retries ({round(total_retry_latency, 1)}ms)",
                    details={
                        "retries": retry_count,
                        "retry_latency_ms": total_retry_latency,
                        "reasons": reasons,
                        "final_status": final_status
                    },
                    suggested_actions=[
                        f"Review failure reasons ({', '.join(reasons) if reasons else 'unknown'}) for {tool_name}",
                        "Configure a circuit breaker and verify tool endpoint uptime"
                    ]
                ))

        return analyses, findings
