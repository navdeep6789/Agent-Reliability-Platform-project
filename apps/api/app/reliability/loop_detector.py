from typing import List, Dict, Any, Tuple
from arp_schemas import ReliabilityFinding, FindingType, Severity, LoopAnalysis

class LoopDetector:
    def __init__(self, repeat_threshold: int = 3):
        self.repeat_threshold = repeat_threshold

    def analyze(self, spans: List[Dict[str, Any]], run_id: str, trace_id: str) -> Tuple[List[LoopAnalysis], List[ReliabilityFinding]]:
        # Extract operation sequence sorted by start_time
        sorted_spans = sorted(spans, key=lambda s: str(s.get("start_time", "")))
        # Filter to tool and llm spans
        op_spans = [s for s in sorted_spans if s.get("span_type") in ("tool", "llm", "retrieval")]

        if len(op_spans) < self.repeat_threshold:
            return [], []

        names = [s.get("name") for s in op_spans]
        analyses: List[LoopAnalysis] = []
        findings: List[ReliabilityFinding] = []

        # Check single-item repeats (e.g. A, A, A, A)
        curr_name = None
        curr_count = 0
        curr_duration = 0.0

        for span in op_spans:
            name = span.get("name")
            dur = float(span.get("duration_ms", 0.0))
            if name == curr_name:
                curr_count += 1
                curr_duration += dur
            else:
                if curr_count >= self.repeat_threshold:
                    self._record_loop(curr_name, [curr_name], curr_count, curr_duration, run_id, trace_id, analyses, findings)
                curr_name = name
                curr_count = 1
                curr_duration = dur

        if curr_count >= self.repeat_threshold:
            self._record_loop(curr_name, [curr_name], curr_count, curr_duration, run_id, trace_id, analyses, findings)

        # Check 2-cycle patterns (e.g. A, B, A, B, A, B)
        if len(op_spans) >= self.repeat_threshold * 2:
            for i in range(len(names) - 5):
                p1, p2 = names[i], names[i+1]
                if p1 != p2 and names[i:i+6] == [p1, p2, p1, p2, p1, p2]:
                    pat = [p1, p2]
                    tot_dur = sum(float(s.get("duration_ms", 0.0)) for s in op_spans[i:i+6])
                    analyses.append(LoopAnalysis(
                        pattern=pat,
                        repetitions=3,
                        duration_ms=round(tot_dur, 2),
                        severity=Severity.HIGH
                    ))
                    findings.append(ReliabilityFinding(
                        id=f"finding_loop_cycle_{run_id}_{i}",
                        run_id=run_id,
                        trace_id=trace_id,
                        finding_type=FindingType.REPEATED_SEQUENCE,
                        severity=Severity.HIGH,
                        title=f"Cyclic loop detected between '{p1}' and '{p2}'",
                        description=f"Agent executed alternating sequence [{p1} -> {p2}] 3 times consecutively without state progression.",
                        target_entity=f"{p1} -> {p2}",
                        observed_metric="3 cycles",
                        details={"pattern": pat, "repetitions": 3, "total_duration_ms": tot_dur},
                        suggested_actions=[
                            "Inspect tool output parsing: the agent might not understand the result of the tool",
                            "Add explicit loop termination condition or max step limit in agent graph"
                        ]
                    ))
                    break

        return analyses, findings

    def _record_loop(
        self,
        name: str,
        pattern: List[str],
        count: int,
        duration: float,
        run_id: str,
        trace_id: str,
        analyses: List[LoopAnalysis],
        findings: List[ReliabilityFinding]
    ):
        analyses.append(LoopAnalysis(
            pattern=pattern,
            repetitions=count,
            duration_ms=round(duration, 2),
            severity=Severity.HIGH if count >= 4 else Severity.MEDIUM
        ))
        findings.append(ReliabilityFinding(
            id=f"finding_loop_{run_id}_{name}",
            run_id=run_id,
            trace_id=trace_id,
            finding_type=FindingType.REPEATED_SEQUENCE,
            severity=Severity.HIGH if count >= 4 else Severity.MEDIUM,
            title=f"Repeated execution loop on '{name}'",
            description=f"Agent executed '{name}' {count} times consecutively, consuming {round(duration / 1000.0, 2)}s of execution time.",
            target_entity=name,
            observed_metric=f"{count} repeated calls",
            details={"pattern": pattern, "repetitions": count, "duration_ms": duration},
            suggested_actions=[
                "Verify whether tool responses are conveying successful termination to the model",
                "Ensure agent has clear halting criteria"
            ]
        ))
