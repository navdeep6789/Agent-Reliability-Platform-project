# Agent Reliability Platform (ARP) — Architecture

The Agent Reliability Platform is an observability, reliability analysis, evaluation, and token cost accounting engine designed for AI agents and LLM applications.

Unlike generic dashboards that display invented numbers, every metric, latency contribution, token count, and policy violation displayed by ARP originates from real telemetry spans and empirical evaluation test runs.

---

## 1. High-Level Telemetry Flow

```text
       ┌────────────────────────┐
       │   AI Agent Application  │
       └───────────┬────────────┘
                   │ ARP Python SDK / OTel Decorators
                   ▼
       ┌────────────────────────┐
       │ OpenTelemetry Collector │ (Port 4317 gRPC / 4318 HTTP)
       └───────────┬────────────┘
                   │ OTLP / HTTP Export
                   ▼
       ┌────────────────────────┐
       │ ARP Ingestion Pipeline │ (Validation, Redaction, OTel Normalization)
       └───────────┬────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌──────────────────┐  ┌──────────────────┐
│ SQLite/PostgreSQL│  │  DuckDB Analytics│
│   (App State)    │  │ (p95, Percentiles│
│ Projects, Policies│ │  Timeseries, Aggs)│
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         └─────────┬───────────┘
                   ▼
       ┌────────────────────────┐
       │   Reliability Engine   │ (Deterministic Trace Analysis:
       └───────────┬────────────┘  Tool Latency %, Retries, Loops, Context Growth)
                   ▼
       ┌────────────────────────┐
       │     Policy Engine      │ (Enforces MAX_LATENCY, MAX_COST, MAX_RETRIES, etc.)
       └───────────┬────────────┘
                   ▼
       ┌────────────────────────┐
       │   Evaluation Engine    │ (25 Benchmark Cases, Version A vs B Regressions)
       └───────────┬────────────┘
                   ▼
       ┌────────────────────────┐
       │   Next.js Workstation  │ (Waterfall Timeline, Inspections, Evidence Tables)
       └────────────────────────┘
```

---

## 2. Core Subsystems

### A. Ingestion & Normalization
* **Standard OTLP Ingestion**: Accepts native OpenTelemetry collector batches at `/api/v1/ingest/otlp`.
* **Direct SDK Ingestion**: Accepts high-throughput JSON batches from the Python SDK at `/api/v1/ingest/spans`.
* **Normalization**: Maps vendor-specific attributes to OpenTelemetry GenAI semantic conventions (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`).

### B. Dual-Engine Storage Architecture
* **Relational Store (PostgreSQL / SQLite)**:
  Maintains tenant isolation, projects, API keys, policies, evaluation suites, and relational run metadata.
* **Analytical Store (DuckDB / ClickHouse)**:
  Processes vector aggregations, percentile latency distributions (`QUANTILE_CONT(duration_ms, 0.95)`), time-series rollups, and multi-attribute searches in sub-milliseconds without table lock contention.

### C. Reliability Engine
An analytical pipeline that inspects spans deterministically:
* **Tool Latency Breakdown**: Calculates actual span contribution percentage relative to total run duration. Flags tools accounting for > 30% of total trace time.
* **Retry & Storm Detector**: Discovers transient errors, sequential attempts on the same tool, total retry latency, and flags retry storms when retries exceed thresholds.
* **Operational Loop Detector**: Identifies alternating sequence cycles (e.g., Tool A -> Model -> Tool A -> Model) and repeated operations without progress.
* **Context Growth Analyzer**: Monitors token accumulation curves across sequential LLM invocations in a run, flagging explosive prompt inflation (+100%, +1,000%).

### D. Policy Engine
Evaluates deterministic guardrails on every completed run:
* `MAX_RUN_LATENCY`: Run duration ceiling.
* `MAX_RUN_COST`: Financial token expenditure ceiling.
* `MAX_TOOL_RETRIES`: Retry limit to prevent cascaded failure.
* `MAX_CONTEXT_TOKENS`: Memory safety ceiling.
* `MIN_EVAL_SCORE`: Quality regression floor.

### E. Evaluation & Regression Engine
* Executes standardized test suites across agent versions.
* Deterministic evaluators: Exact match, JSON schema validation, tool selection correctness, citation presence, response length boundaries, and regex matching.
* Compares Baseline Run (Version A) against Candidate Run (Version B) to pinpoint regressions in score, latency, and cost.
