import time
from arp import observe

class DataAgent:
    def __init__(self, simulate_bad_sql: bool = False, loop_count: int = 1):
        self.simulate_bad_sql = simulate_bad_sql
        self.loop_count = loop_count

    def run(self, analytical_question: str):
        with observe.agent(name="data_agent", version="1.1.0", prompt_version="v1.3") as agent_span:
            agent_span.set_attribute("question", analytical_question)

            # Step 1: LLM Schema plan
            with observe.llm(model="gemini-1.5-pro", provider="google", operation="plan_sql") as llm_plan:
                time.sleep(0.3)
                observe.record_llm_usage(
                    llm_plan,
                    input_tokens=1100,
                    output_tokens=180,
                    completion="Targeting table: billing_events and monthly_active_users"
                )

            # Step 2: Schema discovery tool
            with observe.tool(name="db.get_schema", arguments={"tables": ["billing_events", "users"]}) as schema_tool:
                time.sleep(0.2)
                schema_info = {"columns": ["user_id", "amount_cents", "event_time", "status"]}
                observe.record_tool_result(schema_tool, schema_info)

            # Step 3: Loop or SQL execution
            for i in range(self.loop_count):
                with observe.tool(
                    name="db.execute_sql",
                    arguments={"query": "SELECT user_id, SUM(amount_cents) FROM billing_events WHERE 1=1 GROUP BY 1"}
                ) as sql_tool:
                    time.sleep(0.3)
                    if self.simulate_bad_sql:
                        raise ValueError("SyntaxError: column 'amount_cent' does not exist in relation 'billing_events'")
                    
                    sql_res = {"rows": 142, "total_revenue_usd": 12840.50}
                    observe.record_tool_result(sql_tool, sql_res)

            # Step 4: Final LLM Analysis
            with observe.llm(model="gemini-1.5-pro", provider="google", operation="summarize_analysis") as llm_final:
                time.sleep(0.4)
                observe.record_llm_usage(
                    llm_final,
                    input_tokens=1800,
                    output_tokens=290,
                    completion="Total revenue computed: $12,840.50 across 142 active enterprise accounts."
                )

            return {
                "answer": "Total revenue computed: $12,840.50 across 142 active enterprise accounts.",
                "run_id": agent_span.run_id,
                "trace_id": agent_span.trace_id
            }
