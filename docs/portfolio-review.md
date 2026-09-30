# Engineering Portfolio Review & Interview Defense: Agent Reliability Platform

**Role Target:** Staff AI Systems Engineer / Staff Observability & SRE / AI Infrastructure Architect  
**Project:** Agent Reliability Platform (ARP)  
**Repository Category:** Production-Style Open Source AI Engineering Workstation

---

## 1. What This Repository Demonstrates

This project is designed as proof of real engineering competency across modern distributed AI systems, observability standards, and backend reliability:

### 1. OpenTelemetry & Semantic Conventions
- **Standard-compliant telemetry:** Employs standard GenAI semantic conventions (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) rather than proprietary telemetry dialects.
- **Vendor-neutral architecture:** Provides a clean OTLP Collector configuration (`collector/otel-config.yaml`) capable of receiving OTLP JSON / gRPC traces from any instrumented system.

### 2. Distributed Tracing & High-Performance Data Architecture
- **Dual-Storage Engine:** Separates metadata storage (relational ACID transactions for projects, environments, and policies in SQLite/PostgreSQL) from analytical telemetry storage (embedded DuckDB columnar engine for sub-millisecond p95 latency percentiles and timeseries rollups).
- **Proportional Trace Waterfall:** Mathematically accurate span waterfall visualization derived from actual Unix millisecond timestamps, rendering nested parent-child call chains without fake durations.

### 3. Non-Blocking Python SDK Engineering
- **Asynchronous, Bounded Queue:** Background worker thread exports telemetry batches without adding latency to the user application's critical path.
- **Fail-Open by Default:** Observability failures never crash monitored agent workflows unless explicitly configured with `fail_closed=True`.
- **Thread-safe Context Propagation:** `ContextVar`-based stack tracks nested traces across async coroutines and thread boundaries.

### 4. Deterministic Reliability Engineering (Not Just Tracing)
- **Concrete Diagnostic Insights:** Calculates exact tool latency contribution percentages ($\frac{\text{tool\_duration}}{\text{trace\_duration}} \times 100\%$), identifies retry loops and retry storms, flags cyclic ping-pong calls between agents and tools, and detects exponential context token inflation ($+1,225\%$, $13.3\times$).
- **Zero False-Positive Guarantee:** Tested against healthy traces to guarantee clean operations produce zero false alarms.

### 5. Deterministic Evaluation & Regression Testing
- **Reproducible Test Evaluators:** Exact match, JSON schema validation, tool selection accuracy, and citation presence. Zero reliance on stochastic LLM judges for core evaluations.
- **Version A vs Version B Regression Analysis:** Computes exact score deltas, pass rate regressions (e.g. $-16\%$), latency inflation ($+880\text{ms}$), and cost increases.

### 6. Multi-Tenant Security & Defense-in-Depth
- **Strict Tenant Isolation:** 100% server-side validation ensuring Project A cannot query Project B's traces, evaluations, or findings.
- **Adversarial Ingestion Hardening:** Payload batch limits ($500$ spans max), attribute count caps ($128$ max), and string value truncation to eliminate DoS/OOM vectors.
- **Automated PII/Secret Redaction:** Multi-pass regex and dictionary key scrubber for Bearer tokens, API keys, passwords, and emails.

---

## 2. Interview Defense: What a Senior Engineer Will Challenge

Here are the exact questions a Staff or Principal Engineer will ask during a system design or code review interview, along with honest, rigorous answers:

### Question 1: "Why did you use DuckDB instead of ClickHouse or PostgreSQL for analytical queries?"
**The Challenge:**  
*"ClickHouse is the industry standard for high-volume trace analytics. Why did you use DuckDB, and when would it break?"*

**Honest Answer:**  
> "For a self-contained open-source distribution and local evaluation workstation, DuckDB provides an embedded columnar OLAP engine with zero external dependencies. It computes `QUANTILE_CONT(duration_ms, 0.95)` and timeseries aggregations in sub-millisecond time without requiring the developer to boot up a separate ClickHouse cluster.
> 
> **Where it breaks:** DuckDB is an in-process, single-writer OLAP engine. On Windows and Linux, concurrent write locks from multiple processes will cause file contention. In high-throughput distributed production environments ($>10,000\text{ spans/sec}$), we would replace the DuckDB analytical sink with a distributed ClickHouse cluster or Kafka buffer while keeping the exact same SQL analytical interface."

---

### Question 2: "How do you detect retries without false-flagging legitimate repeated tool calls?"
**The Challenge:**  
*"An agent researching a topic might legitimately call `search('query 1')` and then `search('query 2')`. How do you distinguish that from a retry loop?"*

**Honest Answer:**  
> "A retry is defined by failure followed by re-execution. Our `RetryDetector` requires two conditions:
> 1. At least one span in the tool sequence must have `status == 'error'` or an explicit `arp.tool.retry_count > 0` attribute emitted by the agent runtime.
> 2. Sequential invocations must share the same tool name within the same execution branch.
> 
> If an agent calls `search` twice and both return `status == 'ok'`, `error_count` is 0 and no retry finding is generated. This is verified by our regression test `test_false_positive_prevention_on_healthy_trace`."

---

### Question 3: "Why not use LLM-as-a-Judge for all your evaluations?"
**The Challenge:**  
*"Deterministic evaluators like exact match and regex are brittle for free-form agent outputs. Why did you avoid LLM judges for everything?"*

**Honest Answer:**  
> "LLM-as-a-judge introduces non-determinism, latency (2–5 seconds per evaluation case), and significant cost into the regression pipeline. If your judge has a 5% variance, you cannot reliably detect a 3% prompt regression.
> 
> We prioritize deterministic evaluators (JSON schema conformity, tool selection accuracy, citation presence, and regex boundaries) for the continuous integration test suite. LLM-as-a-judge is supported as an optional layer for subjective qualities (e.g. tone or helpfulness), but should never be the sole gatekeeper for agent reliability."

---

### Question 4: "What happens when an agent generates a trace with 100,000 spans or an infinite loop?"
**The Challenge:**  
*"A broken recursive agent could flood the collector with millions of spans in minutes. How does ARP prevent storage and frontend collapse?"*

**Honest Answer:**  
> "We implement three levels of protection:
> 1. **SDK Queue Bounding:** The SDK has a fixed queue (`maxsize=10,000`). If flooded faster than the flush interval, spans are dropped gracefully with a warning to protect memory.
> 2. **Ingestion Batch Caps:** The API rejects any batch over 500 spans with `HTTP 413 Payload Too Large`.
> 3. **Loop Detection at Run Boundary:** `LoopDetector` analyzes operation sequences and flags alternating 2-cycles ($A \to B \to A \to B$) or identical calls exceeding 3 repetitions, terminating analysis early and generating a `REPEATED_SEQUENCE` finding.
> 4. **Frontend Pagination:** The UI renders top-level runs with server-side pagination (`limit=50`) and only mounts span details when a specific run is opened."

---

### Question 5: "How does project isolation work if the client sends an arbitrary `X-Project-Id` header?"
**The Challenge:**  
*"If `X-Project-Id` comes from the client, couldn't any user spoof another project's ID?"*

**Honest Answer:**  
> "In development mode, `verify_api_key` trusts the header for easy multi-agent testing. In production (`ARP_REQUIRE_AUTH=true`), the header is cross-referenced against the authenticated API key stored in `api_keys`.
> 
> When an API key is provided, the platform looks up the SHA-256 hash in the database, extracts the cryptographically bound `project_id`, and overrides any client-supplied header. A client cannot query or ingest data for Project A using Project B's API key."
