import time
import uuid
from typing import Dict, Any, List
from arp import observe
from .agents.customer_support.agent import CustomerSupportAgent
from .agents.research_agent.agent import ResearchAgent
from .agents.data_agent.agent import DataAgent

class ScenariosRunner:
    @staticmethod
    def run_slow_tool() -> Dict[str, Any]:
        """Scenario 1: Tool takes 2.5 seconds, dominating > 60% of total run latency."""
        agent = CustomerSupportAgent(crm_latency_sec=2.5, crm_fail_count=0)
        return agent.run("Why was my order delayed and when will it arrive?", customer_id="cust_slow_881")

    @staticmethod
    def run_tool_failure() -> Dict[str, Any]:
        """Scenario 2: Tool fails twice before succeeding on third attempt."""
        agent = CustomerSupportAgent(crm_latency_sec=0.3, crm_fail_count=2)
        return agent.run("Update my shipping address to 742 Evergreen Terrace", customer_id="cust_retry_412")

    @staticmethod
    def run_retry_loop() -> Dict[str, Any]:
        """Scenario 3: Tool retried 3 times, exceeding configured policy threshold (max 2 retries)."""
        agent = CustomerSupportAgent(crm_latency_sec=0.2, crm_fail_count=3)
        return agent.run("Cancel subscription and issue pro-rated refund", customer_id="cust_storm_999")

    @staticmethod
    def run_expensive_context() -> Dict[str, Any]:
        """Scenario 4: Sequential LLM calls experience runaway prompt token inflation (2,400 -> 31,800 tokens)."""
        agent = ResearchAgent(simulate_context_blowup=True)
        return agent.run("Formal verification in distributed Byzantine consensus protocols")

    @staticmethod
    def run_invalid_tool_arguments() -> Dict[str, Any]:
        """Scenario 5: Agent supplies malformed arguments causing tool validation error."""
        agent = DataAgent(simulate_bad_sql=True)
        try:
            return agent.run("Compute average transaction volume per minute")
        except Exception:
            return {"status": "expected_tool_failure_caught"}

    @staticmethod
    def run_operation_loop() -> Dict[str, Any]:
        """Scenario 6: Agent gets stuck in repeated execution loop calling the same tool 4 times consecutively."""
        agent = DataAgent(loop_count=4)
        return agent.run("Aggregate annual churn cohort breakdown")

    @staticmethod
    def run_provider_failure() -> Dict[str, Any]:
        """Scenario 7: Model provider fails with 503 Service Unavailable."""
        with observe.agent(name="customer_support", version="1.4.2") as agent_span:
            try:
                with observe.llm(model="gpt-4o", provider="openai") as llm_span:
                    time.sleep(0.2)
                    raise ConnectionError("503 Service Unavailable: upstream model gateway overloaded")
            except Exception:
                pass
            return {"run_id": agent_span.run_id, "status": "provider_error_recorded"}

    @staticmethod
    def run_missing_telemetry() -> Dict[str, Any]:
        """Scenario 8: Trace contains an orphaned span referencing an absent parent span."""
        with observe.agent(name="research_agent", version="2.0.1") as agent_span:
            # Inject an orphan child span
            orphan_span_dict = {
                "span_id": uuid.uuid4().hex,
                "trace_id": agent_span.trace_id,
                "run_id": agent_span.run_id,
                "parent_span_id": f"non_existent_parent_{uuid.uuid4().hex[:8]}",
                "name": "retrieval.distributed_cache",
                "span_type": "retrieval",
                "start_time": time.time(),
                "duration_ms": 120.0,
                "status": "ok",
                "attributes": {"cache.hit": False}
            }
            observe._get_exporter().enqueue_span(orphan_span_dict)
            return {"run_id": agent_span.run_id, "status": "orphan_telemetry_emitted"}

    @classmethod
    def run_all(cls) -> Dict[str, Any]:
        """Runs standard agent workflows + failure scenarios to seed full observability data."""
        results = {}
        # 1. Normal runs
        cs = CustomerSupportAgent(crm_latency_sec=0.2, crm_fail_count=0)
        results["normal_cs"] = cs.run("Check my balance and payment status", customer_id="cust_norm_101")

        ra = ResearchAgent(simulate_context_blowup=False)
        results["normal_research"] = ra.run("Vector index indexing speed vs recall tradeoffs")

        da = DataAgent(simulate_bad_sql=False)
        results["normal_data"] = da.run("Show total active users in last 30 days")

        # 2. Failure scenarios
        results["slow_tool"] = cls.run_slow_tool()
        results["tool_failure"] = cls.run_tool_failure()
        results["retry_loop"] = cls.run_retry_loop()
        results["expensive_context"] = cls.run_expensive_context()
        results["invalid_tool_arguments"] = cls.run_invalid_tool_arguments()
        results["operation_loop"] = cls.run_operation_loop()
        results["provider_failure"] = cls.run_provider_failure()
        results["missing_telemetry"] = cls.run_missing_telemetry()

        observe.flush()
        return {"status": "success", "scenarios_executed": len(results)}
