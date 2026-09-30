# Security, Tenant Isolation, and Privacy

This document outlines the security architecture and privacy policies implemented across the Agent Reliability Platform.

---

## 1. Project & Tenant Isolation

Every telemetry event, span, run, and evaluation dataset is strictly partitioned by `project_id` and `environment`.
* Multi-tenant queries filter by `project_id` at the database level.
* No project can query, view, or correlate telemetry belonging to another project.

---

## 2. API Key Management

* Ingestion API keys are issued with a distinct prefix (`arp_live_...`).
* The raw secret key is displayed **only once** upon generation.
* Keys are stored as SHA-256 hashes in the relational database.
* Full API keys are **never logged** in plaintext in telemetry, application logs, or console outputs.

---

## 3. Defense Against Prompt Injection in Telemetry

Telemetry received by ARP is treated strictly as **untrusted data**:
* Prompt injection attempts (e.g., `"Ignore previous instructions. DROP TABLE runs;"`) are stored as escaped JSON text fields.
* Telemetry text is never passed into shell commands, eval statements, or dynamic SQL queries.
* Relational storage relies entirely on parameterized queries via SQLAlchemy ORM.

---

## 4. Privacy & Regulatory Boundaries

* ARP does not claim automatic compliance with GDPR, HIPAA, or SOC2.
* Developers must configure `capture_prompt_content = False` in sensitive production environments to prevent sensitive PII from entering telemetry stores.
