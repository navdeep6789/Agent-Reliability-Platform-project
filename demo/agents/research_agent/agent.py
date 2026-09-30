import time
from arp import observe

class ResearchAgent:
    def __init__(self, search_latency_sec: float = 0.5, simulate_context_blowup: bool = False):
        self.search_latency_sec = search_latency_sec
        self.simulate_context_blowup = simulate_context_blowup

    def run(self, topic: str):
        with observe.agent(name="research_agent", version="2.0.1", prompt_version="v3.0") as agent_span:
            agent_span.set_attribute("research.topic", topic)

            # Step 1: Planner LLM
            with observe.llm(model="claude-3-5-sonnet-20241022", provider="anthropic", operation="plan_research") as llm_plan:
                time.sleep(0.3)
                observe.record_llm_usage(
                    llm_plan,
                    input_tokens=2400 if self.simulate_context_blowup else 1200,
                    output_tokens=300,
                    completion="Plan: Search recent technical benchmarks, retrieve distributed systems papers, synthesize results."
                )

            # Step 2: Search Tool
            with observe.tool(name="search.web_query", arguments={"query": topic}) as search_tool:
                time.sleep(self.search_latency_sec)
                search_results = [
                    {"title": f"{topic} Performance Deep Dive", "url": "https://arxiv.org/abs/2405.0192"},
                    {"title": f"Observability Patterns in 2026", "url": "https://engineering.blog/patterns"}
                ]
                observe.record_tool_result(search_tool, search_results)

            # Step 3: Vector retrieval
            observe.retrieval(
                name="academic_corpus",
                query=topic,
                documents_count=5,
                latency_ms=350.0
            )

            # If simulating context growth blowup across iterations:
            if self.simulate_context_blowup:
                # Step 4: Iteration 2 LLM
                with observe.llm(model="claude-3-5-sonnet-20241022", provider="anthropic", operation="intermediate_eval") as llm_2:
                    time.sleep(0.3)
                    observe.record_llm_usage(llm_2, input_tokens=5900, output_tokens=450)

                # Step 5: Iteration 3 LLM
                with observe.llm(model="claude-3-5-sonnet-20241022", provider="anthropic", operation="draft_sections") as llm_3:
                    time.sleep(0.4)
                    observe.record_llm_usage(llm_3, input_tokens=14200, output_tokens=850)

                # Step 6: Iteration 4 LLM (Giant prompt inflation)
                with observe.llm(model="claude-3-5-sonnet-20241022", provider="anthropic", operation="final_synthesis") as llm_4:
                    time.sleep(0.6)
                    observe.record_llm_usage(llm_4, input_tokens=31800, output_tokens=1200)
            else:
                # Standard Synthesis LLM
                with observe.llm(model="claude-3-5-sonnet-20241022", provider="anthropic", operation="synthesize_report") as llm_final:
                    time.sleep(0.5)
                    observe.record_llm_usage(
                        llm_final,
                        input_tokens=2200,
                        output_tokens=650,
                        completion=f"Comprehensive technical synthesis for {topic} completed with 2 verified citations."
                    )

            return {
                "report": f"Executive summary on {topic}",
                "run_id": agent_span.run_id,
                "trace_id": agent_span.trace_id
            }
