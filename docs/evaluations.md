# Evaluation & Regression Framework

ARP provides deterministic evaluators and regression testing to validate AI agents before production deployment.

---

## 1. Deterministic Evaluators

Rather than relying entirely on opaque or non-deterministic LLM-as-a-judge scorers, ARP prioritizes fast, deterministic evaluators:

| Evaluator | Description |
| :--- | :--- |
| **ExactMatch** | Strict or normalized string equality verification. |
| **JsonSchema** | Validates JSON format and guarantees presence of required output schema fields. |
| **ToolSelection** | Validates that required tools were invoked and flags missing dependencies. |
| **CitationPresence** | Verifies that required citations, URLs, or academic sources appear in the response. |
| **ResponseLength** | Ensures outputs conform to minimum and maximum character/token boundaries. |
| **RegexPattern** | Enforces structured pattern matching (e.g., ticket IDs, tracking numbers). |

---

## 2. Version Regression Detection (Version A vs Version B)

ARP enables direct comparison between candidate versions:

```json
{
  "baseline_version": "1.0.0",
  "candidate_version": "2.0.0",
  "pass_rate_delta": -16.0,
  "score_delta": -0.151,
  "latency_delta_ms": 880.0,
  "cost_delta_usd": 0.0208,
  "has_regression": true,
  "reasons": [
    "Pass rate dropped by 16.0% (from 92.0% to 76.0%)",
    "Average evaluation score degraded by 0.15 (from 0.94 to 0.79)",
    "Latency regressed by +47.8% (+0.88s)"
  ]
}
```
All numbers are generated from empirical benchmark runs stored in the evaluation database.
