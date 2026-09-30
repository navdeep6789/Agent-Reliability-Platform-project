# Architectural Design Decisions & Tradeoffs

This document details the engineering rationales and tradeoffs behind the core design decisions in the Agent Reliability Platform.

---

## 1. Why OpenTelemetry (OTel)?

* **Rationale**: OpenTelemetry is the vendor-neutral industry standard for distributed tracing. Using standard semantic conventions (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.*`) ensures compatibility with existing observability ecosystems without vendor lock-in.
* **Tradeoffs**: OpenTelemetry's GenAI semantic conventions are actively evolving. We isolate vendor changes behind our `SpanNormalizer` layer.

---

## 2. Why OTLP Collector + Direct SDK Export?

* **Rationale**: Using the OpenTelemetry Collector allows high-volume production deployments to offload batching, retries, and memory limits outside the monitored application. Supporting direct SDK export gives developers a zero-dependency setup for local development.
* **Tradeoffs**: Supporting two ingestion formats requires maintaining both OTLP JSON and direct SDK serializers. We unified this in the ingestion pipeline.

---

## 3. Why Dual Storage: Relational (Postgres/SQLite) + Analytical (DuckDB/ClickHouse)?

* **Rationale**: Relational databases (PostgreSQL/SQLite) excel at ACID compliance, tenant metadata, API key auth, and relational hierarchies. However, calculating 95th percentile latencies and aggregations over millions of spans causes table scan bottlenecks in relational engines. DuckDB/ClickHouse provide columnar vector execution, computing percentiles and aggregations in sub-milliseconds without indexing bloat.
* **Tradeoffs**: Dual storage requires synchronizing span records to the analytical store on ingestion.

---

## 4. Why Deterministic Reliability Rules Over Pure LLM-as-a-Judge?

* **Rationale**: LLM judges are non-deterministic, expensive, slow, and susceptible to prompt injection. Deterministic algorithms (calculating exact mathematical latency percentages, retry count thresholds, regex patterns, schema validation) yield consistent, reproducible reliability findings with zero token cost.
* **Tradeoffs**: Deterministic rules cannot evaluate subjective tone or semantic creativity. LLM judges can be layered as an optional evaluator where necessary.

---

## 5. Why Fail-Open SDK Architecture?

* **Rationale**: Observability must never become a single point of failure. If the collector or ARP backend is down, the agent application must continue serving user traffic uninterrupted.
* **Tradeoffs**: Spans may be dropped during network partitions when the queue exceeds capacity.
