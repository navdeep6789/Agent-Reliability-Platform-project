import uuid
from typing import List, Dict, Any, Optional
from arp_schemas import Policy, PolicyRuleType, PolicySeverity, PolicyViolation

DEFAULT_POLICIES = [
    Policy(
        id="policy_max_latency",
        project_id="proj_default_production",
        name="Maximum Run Latency (5.0s)",
        rule_type=PolicyRuleType.MAX_RUN_LATENCY,
        threshold=5.0, # seconds
        unit="seconds",
        severity=PolicySeverity.CRITICAL,
        enabled=True,
        description="Flag runs taking longer than 5 seconds to complete"
    ),
    Policy(
        id="policy_max_cost",
        project_id="proj_default_production",
        name="Maximum Run Cost ($0.05)",
        rule_type=PolicyRuleType.MAX_RUN_COST,
        threshold=0.05, # USD
        unit="usd",
        severity=PolicySeverity.CRITICAL,
        enabled=True,
        description="Flag runs consuming more than 5 cents of LLM token spend"
    ),
    Policy(
        id="policy_max_retries",
        project_id="proj_default_production",
        name="Maximum Tool Retries (2)",
        rule_type=PolicyRuleType.MAX_TOOL_RETRIES,
        threshold=2.0, # count
        unit="retries",
        severity=PolicySeverity.WARNING,
        enabled=True,
        description="Flag runs where a tool was retried more than 2 times"
    ),
    Policy(
        id="policy_max_context_tokens",
        project_id="proj_default_production",
        name="Maximum Context Tokens (25,000)",
        rule_type=PolicyRuleType.MAX_CONTEXT_TOKENS,
        threshold=25000.0, # tokens
        unit="tokens",
        severity=PolicySeverity.CRITICAL,
        enabled=True,
        description="Prevent runaway context injection exceeding 25,000 tokens"
    ),
    Policy(
        id="policy_min_eval_score",
        project_id="proj_default_production",
        name="Minimum Evaluation Score (0.80)",
        rule_type=PolicyRuleType.MIN_EVAL_SCORE,
        threshold=0.80, # score
        unit="score",
        severity=PolicySeverity.CRITICAL,
        enabled=True,
        description="Flag runs where evaluator score falls below 80%"
    )
]

class PolicyEngine:
    def __init__(self):
        self.policies: Dict[str, Policy] = {p.id: p for p in DEFAULT_POLICIES}

    def list_policies(self, project_id: Optional[str] = None) -> List[Policy]:
        return list(self.policies.values())

    def update_policy(self, policy_id: str, enabled: Optional[bool] = None, threshold: Optional[float] = None) -> Optional[Policy]:
        if policy_id not in self.policies:
            return None
        p = self.policies[policy_id]
        if enabled is not None:
            p.enabled = enabled
        if threshold is not None:
            p.threshold = threshold
        return p

    def evaluate_run(
        self,
        run_dict: Dict[str, Any],
        spans: List[Dict[str, Any]],
        eval_score: Optional[float] = None
    ) -> List[PolicyViolation]:
        violations: List[PolicyViolation] = []
        run_id = run_dict.get("run_id", "")
        trace_id = run_dict.get("trace_id", "")

        duration_sec = float(run_dict.get("duration_ms") or 0.0) / 1000.0
        cost_usd = float(run_dict.get("cost_usd") or 0.0)
        total_retries = int(run_dict.get("retry_count") or 0)
        
        # Calculate max context tokens from llm spans
        max_context_tokens = 0
        for s in spans:
            attrs = s.get("attributes", {})
            in_tok = int(attrs.get("gen_ai.usage.input_tokens") or 0)
            if in_tok > max_context_tokens:
                max_context_tokens = in_tok

        for policy in self.policies.values():
            if not policy.enabled:
                continue

            if policy.rule_type == PolicyRuleType.MAX_RUN_LATENCY:
                if duration_sec > policy.threshold:
                    violations.append(PolicyViolation(
                        id=f"violation_{uuid.uuid4().hex[:8]}",
                        run_id=run_id,
                        trace_id=trace_id,
                        policy_id=policy.id,
                        rule_type=policy.rule_type,
                        severity=policy.severity,
                        threshold_value=policy.threshold,
                        observed_value=round(duration_sec, 2),
                        unit=policy.unit,
                        message=f"Run latency of {round(duration_sec, 2)}s exceeded maximum allowed threshold of {policy.threshold}s"
                    ))

            elif policy.rule_type == PolicyRuleType.MAX_RUN_COST:
                if cost_usd > policy.threshold:
                    violations.append(PolicyViolation(
                        id=f"violation_{uuid.uuid4().hex[:8]}",
                        run_id=run_id,
                        trace_id=trace_id,
                        policy_id=policy.id,
                        rule_type=policy.rule_type,
                        severity=policy.severity,
                        threshold_value=policy.threshold,
                        observed_value=cost_usd,
                        unit=policy.unit,
                        message=f"Run cost of ${cost_usd:.4f} exceeded policy limit of ${policy.threshold:.2f}"
                    ))

            elif policy.rule_type == PolicyRuleType.MAX_TOOL_RETRIES:
                if total_retries > policy.threshold:
                    violations.append(PolicyViolation(
                        id=f"violation_{uuid.uuid4().hex[:8]}",
                        run_id=run_id,
                        trace_id=trace_id,
                        policy_id=policy.id,
                        rule_type=policy.rule_type,
                        severity=policy.severity,
                        threshold_value=policy.threshold,
                        observed_value=float(total_retries),
                        unit=policy.unit,
                        message=f"Observed {total_retries} retries exceeding threshold limit of {int(policy.threshold)}"
                    ))

            elif policy.rule_type == PolicyRuleType.MAX_CONTEXT_TOKENS:
                if max_context_tokens > policy.threshold:
                    violations.append(PolicyViolation(
                        id=f"violation_{uuid.uuid4().hex[:8]}",
                        run_id=run_id,
                        trace_id=trace_id,
                        policy_id=policy.id,
                        rule_type=policy.rule_type,
                        severity=policy.severity,
                        threshold_value=policy.threshold,
                        observed_value=float(max_context_tokens),
                        unit=policy.unit,
                        message=f"Prompt context of {max_context_tokens:,} tokens exceeded safety boundary of {int(policy.threshold):,}"
                    ))

            elif policy.rule_type == PolicyRuleType.MIN_EVAL_SCORE:
                if eval_score is not None and eval_score < policy.threshold:
                    violations.append(PolicyViolation(
                        id=f"violation_{uuid.uuid4().hex[:8]}",
                        run_id=run_id,
                        trace_id=trace_id,
                        policy_id=policy.id,
                        rule_type=policy.rule_type,
                        severity=policy.severity,
                        threshold_value=policy.threshold,
                        observed_value=eval_score,
                        unit=policy.unit,
                        message=f"Evaluator score {eval_score:.2f} fell below required minimum of {policy.threshold:.2f}"
                    ))

        return violations

# Global policy engine instance
policy_engine = PolicyEngine()
