from typing import Dict, Any, List
from arp_schemas import RegressionReport

class RegressionAnalyzer:
    @staticmethod
    def compare_runs(baseline: Dict[str, Any], candidate: Dict[str, Any]) -> RegressionReport:
        b_pass_rate = float(baseline.get("pass_rate") or 0.0)
        c_pass_rate = float(candidate.get("pass_rate") or 0.0)
        pass_rate_delta = round(c_pass_rate - b_pass_rate, 2)

        b_score = float(baseline.get("average_score") or 0.0)
        c_score = float(candidate.get("average_score") or 0.0)
        score_delta = round(c_score - b_score, 3)

        b_lat = float(baseline.get("average_latency_ms") or 0.0)
        c_lat = float(candidate.get("average_latency_ms") or 0.0)
        latency_delta = round(c_lat - b_lat, 1)

        b_cost = float(baseline.get("total_cost_usd") or 0.0)
        c_cost = float(candidate.get("total_cost_usd") or 0.0)
        cost_delta = round(c_cost - b_cost, 4)

        reasons = []
        has_regression = False

        # 1. Pass rate drop
        if pass_rate_delta < -3.0:
            has_regression = True
            reasons.append(f"Pass rate dropped by {abs(pass_rate_delta)}% (from {b_pass_rate}% to {c_pass_rate}%)")

        # 2. Score drop
        if score_delta < -0.05:
            has_regression = True
            reasons.append(f"Average evaluation score degraded by {abs(score_delta):.2f} (from {b_score:.2f} to {c_score:.2f})")

        # 3. Latency regression (> 25% slower and > 500ms slower)
        if b_lat > 0 and (c_lat - b_lat) / b_lat > 0.25 and (c_lat - b_lat) > 500.0:
            has_regression = True
            reasons.append(f"Latency regressed by +{round((c_lat - b_lat) / b_lat * 100.0, 1)}% (+{round(latency_delta/1000.0, 2)}s)")

        # 4. Cost spike (> 30% higher)
        if b_cost > 0 and (c_cost - b_cost) / b_cost > 0.30:
            reasons.append(f"Execution cost increased by +{round((c_cost - b_cost) / b_cost * 100.0, 1)}% (+${cost_delta:.4f})")

        return RegressionReport(
            baseline_version=candidate.get("baseline_version") or baseline.get("agent_version", "1.0.0"),
            candidate_version=candidate.get("agent_version", "2.0.0"),
            agent_name=candidate.get("agent_name", "unknown"),
            pass_rate_delta=pass_rate_delta,
            score_delta=score_delta,
            latency_delta_ms=latency_delta,
            cost_delta_usd=cost_delta,
            has_regression=has_regression,
            reasons=reasons,
            baseline_run_id=baseline.get("id", ""),
            candidate_run_id=candidate.get("id", "")
        )
