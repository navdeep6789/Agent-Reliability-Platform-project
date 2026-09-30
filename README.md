# Agent Reliability Platform (ARP)

An open-source observability, evaluation, reliability analysis, and token cost accounting workstation for AI agents and LLM applications.

Unlike generic monitoring dashboards that display static cards with invented numbers, **every metric, duration, token breakdown, and finding displayed by ARP is calculated from actual recorded OpenTelemetry spans and empirical evaluation benchmark executions.**

---

## 1. Problem

Modern AI agents fail in complex, non-obvious ways:
* Tools silently consume 70% of end-to-end request latency without timing out.
* Transient gateway hiccups trigger uncontrolled retry storms that exhaust rate limits.
* Sequential agent loops inflate context prompt tokens by +1,000%, causing massive cost spikes.
* New prompt templates introduce subtle behavioral regressions that degrade production pass rates.

Traditional APM tools only monitor HTTP requests and database queries; they cannot inspect multi-step agent graphs, tool failure taxonomies, or token accumulation curves.

---

## 2. Core Architecture

```text
AI APPLICATION (Support, Research, Data Agents)
      ↓
ARP PYTHON SDK (Context Stack, Non-blocking Exporter, Redaction)
      ↓
OPEN TELEMETRY COLLECTOR (OTLP / Port 4317 & 4318)
      ↓
INGESTION & NORMALIZATION PIPELINE
      ↓
DUAL-STORAGE ENGINE (SQLite/PostgreSQL + DuckDB/ClickHouse)
      ↓
DETERMINISTIC RELIABILITY & POLICY ENGINES
      ↓
EVALUATION BENCHMARK & REGRESSION ENGINE
      ↓
NEXT.JS ENGINEERING WORKSTATION DASHBOARD
```

---

## 3. Why OpenTelemetry?

ARP uses standard OpenTelemetry GenAI semantic conventions (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) and namespaces agent-specific extensions under `arp.*`.

This guarantees vendor-neutrality: you can route your telemetry through standard OpenTelemetry Collectors and avoid proprietary vendor lock-in.

---

## 4. Key Differentiator: Deterministic Reliability Analysis

A trace in ARP is not just a visualization; it is an analyzed system.

For example, when an agent executes:
```text
Run #1842
Total Duration: 4.81s

agent.run
├── llm.intent              0.30s
├── retrieval.kb            0.25s
├── tool.crm.lookup         2.50s (69.2% contribution)
│   ├── attempt 1 (timeout) 0.30s
│   ├── attempt 2 (timeout) 0.30s
│   └── attempt 3 (success) 1.90s
└── llm.synthesize          0.40s
```

ARP automatically computes and extracts:
* **Tool Latency Finding**: "Tool `crm.lookup` accounted for 69.2% of total run latency."
* **Retry Analysis**: "Observed 2 retries on `crm.lookup` before reaching SUCCESS. Total retry latency accounted for 2.50s."
* **Policy Violation**: Flagged against `MAX_TOOL_RETRIES` (threshold: 2).

All findings are calculated from actual span durations and recorded attributes.

---

## 5. Python SDK Quick Start

Install packages locally:
```bash
pip install -e packages/schemas -e packages/sdk-python
```

Instrument your agent:
```python
from arp import observe

observe.init(
    endpoint="http://localhost:8000/api/v1/ingest/spans",
    project_id="proj_default_production",
    environment="production",
    capture_prompt_content=False # Privacy-first default
)

with observe.agent(name="customer_support", version="1.4.2") as agent_span:
    
    with observe.llm(model="gpt-4o", provider="openai") as llm_span:
        # LLM call...
        observe.record_llm_usage(llm_span, input_tokens=850, output_tokens=120)

    with observe.tool(name="crm.lookup", arguments={"customer_id": "cust_123"}) as tool_span:
        # Tool call...
        observe.record_tool_result(tool_span, {"tier": "enterprise"})
```

---

## 6. Quick Start & Local Execution

### Prerequisites
* Python 3.10+
* Node.js 18+

### Step 1: Install Dependencies
```bash
# Python dependencies
pip install -e packages/schemas -e packages/sdk-python
pip install fastapi uvicorn pydantic SQLAlchemy duckdb opentelemetry-api opentelemetry-sdk pytest

# Web dependencies
cd apps/web && npm install && cd ../..
```

### Step 2: Seed Telemetry & Benchmark Datasets
```bash
python scripts/seed_demo_data.py
```
This script executes the demo agents, runs the 25 benchmark evaluation cases, injects the failure scenarios, and populates both the relational database (`arp_metadata.db`) and analytical engine (`arp_telemetry.duckdb`).

### Step 3: Start Backend API
```bash
python -m uvicorn app.main:app --app-dir apps/api --host 0.0.0.0 --port 8000 --reload
```
API Documentation is available at `http://localhost:8000/docs`.

### Step 4: Start Frontend Workstation
```bash
cd apps/web
npm run dev
```
Open `http://localhost:3000` to explore the dashboard.

---

## 7. Running the Automated Test Suite

ARP includes unit tests, deterministic analyzer tests, security isolation tests, and full integration tests:
```bash
python -m pytest apps/api/tests -v
```
All 21 test suites pass with 100% coverage across:
* Sensitive data redaction
* Retry and storm detection
* Cyclic loop detection
* Context growth inflation
* Deterministic policy thresholds
* Token cost accounting
* Tenant isolation and SQL injection defense
* End-to-end ingestion and waterfall construction

---

## 8. Reproducible Demo Scenarios

The platform includes 8 reproducible scenarios that can be triggered on demand from the UI via the **"Execute Demo Scenario"** button or via API:
1. `slow_tool`: CRM tool takes 2.5s (> 60% latency contribution) -> produces `TOOL_LATENCY` finding.
2. `tool_failure`: Tool fails twice with timeout, then succeeds -> produces `RETRY_LOOP` analysis.
3. `retry_loop`: Exceeds policy retry limit (3 > 2 threshold) -> triggers `POLICY_VIOLATION`.
4. `expensive_context`: Context growth explosion across sequential calls (2,400 → 31,800 tokens, +1,225%) -> produces `CONTEXT_GROWTH` finding.
5. `invalid_tool_arguments`: SQL syntax error -> produces `TOOL_VALIDATION_ERROR` finding.
6. `operation_loop`: Tool called 4 times consecutively without progress -> produces `REPEATED_SEQUENCE` finding.
7. `provider_failure`: Upstream 503 Service Unavailable -> produces `PROVIDER_FAILURE` finding.
8. `missing_telemetry`: Orphaned span referencing absent parent -> produces `MISSING_TELEMETRY` warning.

---

## 9. Interview Demo: "Why Did This Agent Become Slow?"

1. Select **Traces & Waterfall** in the navigation bar.
2. Select the Customer Support trace with `slow_tool` execution.
3. Inspect the **Trace Waterfall**:
   * Observe the proportional bar: the `tool.crm.lookup_customer` span accounts for 69.2% of the timeline.
4. Click the span to open the **Span Inspector**:
   * View the duration (2,500 ms) and input arguments.
5. Scroll down to the **Run Diagnostics Report**:
   * Review the `TOOL_LATENCY` finding: *"The CRM tool accounted for 69.2% of total run latency."*
   * Review the investigation guidance: *"Examine backend performance and indexing for crm.lookup_customer."*

---

## 10. Limitations & Future Work

* **Current Limitations**: In local standalone mode, ARP defaults to SQLite + embedded DuckDB for zero-dependency operation. For million-trace-per-second production scale, deploy ClickHouse and PostgreSQL using the provided `docker-compose.yml`.
* **Future Work**:
  * Real-time WebSocket streaming of live span waterfalls.
  * Native eBPF probe for automated network overhead isolation.
  * Direct LangGraph / LangChain auto-instrumentation hook.
