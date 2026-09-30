import uuid
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..storage.database import SessionLocal
from ..storage.models import EvaluationDatasetModel, EvaluationRunModel, EvaluationCaseResultModel
from .evaluators import (
    ExactMatchEvaluator,
    JsonSchemaEvaluator,
    ToolSelectionEvaluator,
    CitationPresenceEvaluator,
    ResponseLengthEvaluator,
    RegexPatternEvaluator
)

class EvaluationEngine:
    def run_suite(
        self,
        dataset_id: str,
        agent_fn: Any, # Callable[[Dict[str, Any]], Dict[str, Any]]
        agent_name: str,
        agent_version: str = "1.0.0",
        prompt_version: Optional[str] = None
    ) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            dataset = db.query(EvaluationDatasetModel).filter(EvaluationDatasetModel.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            cases = json.loads(dataset.cases_json or "[]")
            eval_run_id = f"eval_run_{uuid.uuid4().hex[:10]}"

            case_results = []
            passed_count = 0
            failed_count = 0
            total_score = 0.0
            total_latency = 0.0
            total_tokens = 0
            total_cost = 0.0
            failure_breakdown: Dict[str, int] = {}

            for c in cases:
                c_id = c.get("id")
                c_name = c.get("name", "Unnamed Case")
                c_input = c.get("input", {})
                expected_output = c.get("expected_output")
                expected_tools = c.get("expected_tools")
                required_citations = c.get("required_citations")
                expected_schema = c.get("expected_schema")
                eval_type = c.get("evaluator_type", "exact_match")

                start_t = time.time()
                try:
                    # Invoke agent
                    agent_res = agent_fn(c_input)
                    latency_ms = (time.time() - start_t) * 1000.0
                    
                    actual_output = agent_res.get("output", "")
                    invoked_tools = agent_res.get("tools_invoked", [])
                    tokens_used = agent_res.get("tokens_used", 0)
                    cost_usd = agent_res.get("cost_usd", 0.0)
                    run_id = agent_res.get("run_id")

                    # Run appropriate evaluators
                    res = None
                    if eval_type == "json_schema":
                        res = JsonSchemaEvaluator.evaluate(actual_output, expected_schema)
                    elif eval_type == "tool_selection":
                        res = ToolSelectionEvaluator.evaluate(invoked_tools, expected_tools)
                    elif eval_type == "citation_presence":
                        res = CitationPresenceEvaluator.evaluate(actual_output, required_citations or [])
                    elif eval_type == "response_length":
                        res = ResponseLengthEvaluator.evaluate(actual_output)
                    elif eval_type == "regex_pattern":
                        res = RegexPatternEvaluator.evaluate(actual_output, c.get("pattern", ".*"))
                    else:
                        res = ExactMatchEvaluator.evaluate(actual_output, expected_output)

                    passed = res.passed
                    score = res.score
                    fail_reason = res.failure_reason

                except Exception as e:
                    latency_ms = (time.time() - start_t) * 1000.0
                    passed = False
                    score = 0.0
                    fail_reason = f"Execution error: {str(e)}"
                    actual_output = None
                    tokens_used = 0
                    cost_usd = 0.0
                    run_id = None

                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
                    cat = eval_type
                    failure_breakdown[cat] = failure_breakdown.get(cat, 0) + 1

                total_score += score
                total_latency += latency_ms
                total_tokens += tokens_used
                total_cost += cost_usd

                # Save case result
                db_case = EvaluationCaseResultModel(
                    id=f"case_res_{uuid.uuid4().hex[:10]}",
                    eval_run_id=eval_run_id,
                    case_id=c_id,
                    case_name=c_name,
                    run_id=run_id,
                    passed=passed,
                    score=score,
                    evaluator_type=eval_type,
                    actual_output=actual_output,
                    expected_output=expected_output,
                    failure_reason=fail_reason,
                    latency_ms=round(latency_ms, 1),
                    tokens_used=tokens_used,
                    cost_usd=round(cost_usd, 6),
                    details_json=json.dumps(c)
                )
                db.add(db_case)
                case_results.append(db_case)

            total_cases = len(cases)
            pass_rate = round((passed_count / max(total_cases, 1)) * 100.0, 1)
            avg_score = round(total_score / max(total_cases, 1), 3)
            avg_latency = round(total_latency / max(total_cases, 1), 1)

            eval_run = EvaluationRunModel(
                id=eval_run_id,
                dataset_id=dataset_id,
                dataset_name=dataset.name,
                project_id=dataset.project_id,
                agent_name=agent_name,
                agent_version=agent_version,
                prompt_version=prompt_version,
                total_cases=total_cases,
                passed_cases=passed_count,
                failed_cases=failed_count,
                pass_rate=pass_rate,
                average_score=avg_score,
                average_latency_ms=avg_latency,
                total_cost_usd=round(total_cost, 4),
                failure_breakdown_json=json.dumps(failure_breakdown)
            )
            db.add(eval_run)
            db.commit()

            return {
                "id": eval_run_id,
                "dataset_id": dataset_id,
                "dataset_name": dataset.name,
                "agent_name": agent_name,
                "agent_version": agent_version,
                "prompt_version": prompt_version,
                "total_cases": total_cases,
                "passed_cases": passed_count,
                "failed_cases": failed_count,
                "pass_rate": pass_rate,
                "average_score": avg_score,
                "average_latency_ms": avg_latency,
                "total_cost_usd": round(total_cost, 4),
                "failure_breakdown": failure_breakdown
            }
        finally:
            db.close()

# Global evaluation engine instance
evaluation_engine = EvaluationEngine()
