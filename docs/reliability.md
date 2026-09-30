# Reliability Engine & Diagnostics

The core differentiator of ARP is **Reliability Analysis**. A trace is not merely a tree of boxes; it is analyzed mathematically to extract actionable operational findings.

---

## 1. Tool Latency & Contribution Analysis

A trace reports:
```text
Run #1842
Total Duration: 4.81s

LLM Intent:        0.30s
Retrieval:         0.25s
CRM Lookup Tool:   2.50s (69.2% of trace duration)
Final LLM:         0.40s
```

ARP calculates exact span contribution percentages:
$$\text{Contribution} = \left(\frac{\text{Span Duration}}{\text{Total Trace Duration}}\right) \times 100\%$$

When a tool accounts for $\ge 30\%$ of total trace duration, ARP raises a `TOOL_LATENCY` finding with targeted investigation areas.

---

## 2. Retry Analysis & Storm Detection

ARP detects retry patterns across spans:
* **Sequential Retries**: Discovers when tool calls fail, records individual step latency, and verifies whether the final attempt succeeded.
* **Retry Storms**: Flags when a tool exceeds 3 retries or accounts for disproportionate latency, advising circuit breakers.

---

## 3. Operational Loop Detection

Detects repetitive cycles without state change:
* Single tool loops: $A \to A \to A \to A$ (exceeding repetition threshold).
* Alternating cyclic loops: $A \to B \to A \to B \to A \to B$.

---

## 4. Context Growth Analysis

Tracks token accumulation across sequential model calls:
```text
Call 1:  2,400 tokens
Call 2:  5,900 tokens
Call 3: 14,200 tokens
Call 4: 31,800 tokens
```
Calculates exact multiplier (13.3x) and percentage inflation (+1,225%), advising sliding-window context pruning.
