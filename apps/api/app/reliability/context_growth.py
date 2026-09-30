from typing import List, Dict, Any, Optional, Tuple
from arp_schemas import (
    ReliabilityFinding, FindingType, Severity, ContextGrowthAnalysis, ContextGrowthStep
)

class ContextGrowthAnalyzer:
    def __init__(self, growth_threshold_multiplier: float = 3.0, min_initial_tokens: int = 500):
        self.growth_threshold_multiplier = growth_threshold_multiplier
        self.min_initial_tokens = min_initial_tokens

    def analyze(self, spans: List[Dict[str, Any]], run_id: str, trace_id: str) -> Tuple[Optional[ContextGrowthAnalysis], List[ReliabilityFinding]]:
        llm_spans = [s for s in spans if s.get("span_type") == "llm" or s.get("name", "").startswith("llm.")]
        llm_spans.sort(key=lambda s: str(s.get("start_time", "")))

        if len(llm_spans) < 2:
            return None, []

        steps: List[ContextGrowthStep] = []
        token_series: List[int] = []

        initial_tokens = 0
        for idx, span in enumerate(llm_spans):
            attrs = span.get("attributes", {})
            in_tok = int(attrs.get("gen_ai.usage.input_tokens") or 0)
            out_tok = int(attrs.get("gen_ai.usage.output_tokens") or 0)
            model = attrs.get("gen_ai.request.model") or span.get("name")

            if idx == 0:
                initial_tokens = in_tok
                delta = 0.0
            else:
                base = initial_tokens if initial_tokens > 0 else 1
                delta = round(((in_tok - initial_tokens) / base) * 100.0, 1)

            steps.append(ContextGrowthStep(
                call_index=idx + 1,
                span_id=span.get("span_id", ""),
                model=model,
                input_tokens=in_tok,
                output_tokens=out_tok,
                delta_percent=delta
            ))
            token_series.append(in_tok)

        peak_tokens = max(token_series) if token_series else 0
        base_tokens = initial_tokens if initial_tokens > 0 else (token_series[0] if token_series else 1)

        multiplier = round(peak_tokens / (base_tokens or 1), 1)
        growth_percent = round(((peak_tokens - base_tokens) / (base_tokens or 1)) * 100.0, 1)

        is_abnormal = (multiplier >= self.growth_threshold_multiplier and peak_tokens > 5000) or growth_percent > 300.0

        analysis = ContextGrowthAnalysis(
            initial_tokens=base_tokens,
            peak_tokens=peak_tokens,
            growth_multiplier=multiplier,
            growth_percent=growth_percent,
            steps=steps,
            is_abnormal=is_abnormal
        )

        findings: List[ReliabilityFinding] = []
        if is_abnormal:
            findings.append(ReliabilityFinding(
                id=f"finding_context_growth_{run_id}",
                run_id=run_id,
                trace_id=trace_id,
                finding_type=FindingType.CONTEXT_GROWTH,
                severity=Severity.HIGH if multiplier >= 5.0 else Severity.MEDIUM,
                title=f"Explosive context growth detected (+{int(growth_percent)}%)",
                description=(
                    f"Context grew by +{int(growth_percent)}% across {len(llm_spans)} sequential model calls. "
                    f"The final invocation required {multiplier}× the initial prompt size ({base_tokens:,} → {peak_tokens:,} tokens)."
                ),
                target_entity="context_accumulator",
                observed_metric=f"+{int(growth_percent)}% ({multiplier}x)",
                details={
                    "initial_tokens": base_tokens,
                    "peak_tokens": peak_tokens,
                    "multiplier": multiplier,
                    "calls_count": len(llm_spans),
                    "steps": [s.model_dump() for s in steps]
                },
                suggested_actions=[
                    "Implement sliding window context pruning or conversation summarization",
                    "Truncate raw tool call JSON payloads before appending them back into the message history",
                    "Review intermediate system prompts being re-injected each iteration"
                ]
            ))

        return analysis, findings
