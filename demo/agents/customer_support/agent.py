import time
from arp import observe

class CustomerSupportAgent:
    def __init__(self, crm_latency_sec: float = 0.4, crm_fail_count: int = 0):
        self.crm_latency_sec = crm_latency_sec
        self.crm_fail_count = crm_fail_count
        self.current_crm_attempts = 0

    def run(self, user_query: str, customer_id: str = "cust_9821"):
        with observe.agent(name="customer_support", version="1.4.2", prompt_version="v2.1") as agent_span:
            agent_span.set_attribute("customer.id", customer_id)
            agent_span.set_attribute("user.query", user_query)

            # Step 1: Initial LLM classification
            with observe.llm(model="gpt-4o", provider="openai", operation="classify_intent") as llm_1:
                time.sleep(0.3)
                observe.record_llm_usage(
                    llm_1,
                    input_tokens=850,
                    output_tokens=120,
                    completion="Intent classified: Order status inquiry and refund request."
                )

            # Step 2: Knowledge Retrieval
            observe.retrieval(
                name="support_kb",
                query="refund eligibility and delivery policy",
                documents_count=3,
                latency_ms=250.0
            )

            # Step 3: CRM Tool lookup
            crm_result = None
            retry_count = 0
            while retry_count <= self.crm_fail_count:
                try:
                    with observe.tool(
                        name="crm.lookup_customer",
                        arguments={"customer_id": customer_id},
                        retry_count=retry_count
                    ) as tool_span:
                        time.sleep(self.crm_latency_sec)
                        if retry_count < self.crm_fail_count:
                            raise TimeoutError(f"Connection to CRM gateway timed out after {self.crm_latency_sec}s")
                        
                        crm_result = {
                            "customer_id": customer_id,
                            "tier": "enterprise",
                            "status": "active",
                            "open_tickets": 1,
                            "recent_order_id": "ord_8829"
                        }
                        observe.record_tool_result(tool_span, crm_result, status="ok")
                        break
                except Exception as e:
                    retry_count += 1
                    if retry_count > self.crm_fail_count:
                        raise

            # Step 4: Final LLM synthesis
            with observe.llm(model="gpt-4o", provider="openai", operation="synthesize_response") as llm_2:
                time.sleep(0.4)
                observe.record_llm_usage(
                    llm_2,
                    input_tokens=1450,
                    output_tokens=320,
                    completion=f"Hello! Your order ord_8829 is currently in transit and scheduled for delivery tomorrow."
                )

            return {
                "response": "Hello! Your order ord_8829 is currently in transit and scheduled for delivery tomorrow.",
                "customer": crm_result,
                "run_id": agent_span.run_id,
                "trace_id": agent_span.trace_id
            }
