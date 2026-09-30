# Python SDK (`arp`) — Developer Guide

The official Python SDK provides non-blocking, fail-safe instrumentation for AI agents.

---

## 1. Quick Start

```python
from arp import observe

# 1. Initialize SDK
observe.init(
    endpoint="http://localhost:8000/api/v1/ingest/spans",
    project_id="proj_default_production",
    environment="production",
    capture_prompt_content=False, # Privacy first
    capture_tool_arguments=True
)

# 2. Instrument Agent Run
with observe.agent(name="support_agent", version="1.2.0") as agent:
    
    # 3. Instrument Model Call
    with observe.llm(model="gpt-4o", provider="openai") as llm_span:
        # Call model...
        observe.record_llm_usage(llm_span, input_tokens=1200, output_tokens=250)

    # 4. Instrument Tool Call
    with observe.tool(name="crm.lookup", arguments={"id": "cust_123"}) as tool_span:
        # Execute tool...
        result = {"tier": "enterprise"}
        observe.record_tool_result(tool_span, result)
```

---

## 2. Content Privacy & Redaction Pipeline

Telemetry can contain sensitive customer data. The SDK ensures data is protected before export:
* `capture_prompt_content = False`: Disables recording raw prompt strings.
* `capture_completion_content = False`: Disables recording completion texts.
* `capture_tool_arguments = False`: Disables recording tool input dictionaries.
* `capture_tool_results = False`: Disables recording tool returned payloads.

### Automated Redaction Pipeline
Even when content capture is enabled, the redaction pipeline automatically detects and scrubs:
* API keys (e.g., `sk-...`, Bearer tokens, GitHub tokens)
* Email addresses
* Passwords, secrets, and auth headers
* Configurable sensitive JSON dictionary keys

---

## 3. Resilient Observability (Fail-Open)

If the ARP backend or collector is temporarily unavailable, network requests time out, or the collector crashes:
* The SDK's background exporter will log a warning and discard spans if queue capacity is exceeded.
* **The host AI agent application will NEVER crash due to telemetry failures.**
* Observability must never become a single point of failure for monitored applications.
