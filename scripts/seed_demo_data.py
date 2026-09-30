import os
import sys
import json
import logging
from datetime import datetime

# Setup project root path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "apps", "api"))

from app.storage.database import init_db, SessionLocal
from app.storage.models import EvaluationDatasetModel, EvaluationRunModel, EvaluationCaseResultModel, ProjectModel
from app.config import settings
from app.evaluations.regressions import RegressionAnalyzer
from demo.scenarios_runner import ScenariosRunner
from arp import observe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

def seed_data():
    logger.info("Initializing ARP Database tables...")
    init_db()

    db = SessionLocal()
    try:
        # 1. Ensure default project exists
        proj = db.query(ProjectModel).filter(ProjectModel.id == settings.DEFAULT_PROJECT_ID).first()
        if not proj:
            proj = ProjectModel(
                id=settings.DEFAULT_PROJECT_ID,
                name="Default Production Project",
                description="Default production tenant"
            )
            db.add(proj)
            db.commit()

        # 2. Seed Evaluation Dataset
        dataset_path = os.path.join(BASE_DIR, "evaluations", "datasets", "benchmark_cases.json")
        with open(dataset_path, "r", encoding="utf-8") as f:
            cases = json.load(f)

        dataset_id = "dataset_core_benchmarks"
        existing_ds = db.query(EvaluationDatasetModel).filter(EvaluationDatasetModel.id == dataset_id).first()
        if not existing_ds:
            logger.info("Creating Benchmark Evaluation Dataset...")
            existing_ds = EvaluationDatasetModel(
                id=dataset_id,
                project_id=settings.DEFAULT_PROJECT_ID,
                name="Agent Core Reliability Benchmark Suite",
                description="25 comprehensive test cases validating schema compliance, tool selection, citations, and error handling",
                agent_target="multi_agent",
                version="1.0.0",
                total_cases=len(cases),
                cases_json=json.dumps(cases)
            )
            db.add(existing_ds)
            db.commit()

        # 3. Create Baseline Evaluation Run (v1.0 - 92% pass rate, fast, reliable)
        eval_run_v1 = db.query(EvaluationRunModel).filter(EvaluationRunModel.id == "eval_run_baseline_v1").first()
        if not eval_run_v1:
            logger.info("Recording Baseline Evaluation Run (v1.0)...")
            eval_run_v1 = EvaluationRunModel(
                id="eval_run_baseline_v1",
                dataset_id=dataset_id,
                dataset_name="Agent Core Reliability Benchmark Suite",
                project_id=settings.DEFAULT_PROJECT_ID,
                agent_name="customer_support",
                agent_version="1.0.0",
                prompt_version="v1.0-stable",
                total_cases=25,
                passed_cases=23,
                failed_cases=2,
                pass_rate=92.0,
                average_score=0.942,
                average_latency_ms=1840.0,
                total_cost_usd=0.0384,
                failure_breakdown_json=json.dumps({"tool_selection": 1, "exact_match": 1})
            )
            db.add(eval_run_v1)

            # Add sample case results for baseline
            for idx, c in enumerate(cases):
                passed = idx not in (4, 11)
                db.add(EvaluationCaseResultModel(
                    id=f"case_res_base_{idx}",
                    eval_run_id="eval_run_baseline_v1",
                    case_id=c.get("id"),
                    case_name=c.get("name"),
                    passed=passed,
                    score=1.0 if passed else 0.4,
                    evaluator_type=c.get("evaluator_type", "tool_selection"),
                    actual_output="Simulated accurate response from baseline agent",
                    expected_output=c.get("expected_output") or "Expected valid output",
                    failure_reason=None if passed else "Minor tool argument format discrepancy",
                    latency_ms=1800.0,
                    tokens_used=1850,
                    cost_usd=0.0015
                ))
            db.commit()

        # 4. Create Candidate Evaluation Run (v2.0 - 76% pass rate with Regression)
        eval_run_v2 = db.query(EvaluationRunModel).filter(EvaluationRunModel.id == "eval_run_candidate_v2").first()
        if not eval_run_v2:
            logger.info("Recording Candidate Evaluation Run (v2.0 with detected regression)...")
            eval_run_v2 = EvaluationRunModel(
                id="eval_run_candidate_v2",
                dataset_id=dataset_id,
                dataset_name="Agent Core Reliability Benchmark Suite",
                project_id=settings.DEFAULT_PROJECT_ID,
                agent_name="customer_support",
                agent_version="2.0.0",
                prompt_version="v2.0-experimental",
                total_cases=25,
                passed_cases=19,
                failed_cases=6,
                pass_rate=76.0,
                average_score=0.791,
                average_latency_ms=2720.0,
                total_cost_usd=0.0592,
                failure_breakdown_json=json.dumps({"tool_selection": 3, "response_length": 2, "citation_presence": 1})
            )
            db.add(eval_run_v2)

            for idx, c in enumerate(cases):
                passed = idx not in (2, 4, 8, 11, 15, 20)
                db.add(EvaluationCaseResultModel(
                    id=f"case_res_cand_{idx}",
                    eval_run_id="eval_run_candidate_v2",
                    case_id=c.get("id"),
                    case_name=c.get("name"),
                    passed=passed,
                    score=1.0 if passed else 0.2,
                    evaluator_type=c.get("evaluator_type", "tool_selection"),
                    actual_output="Simulated candidate output with regressions",
                    expected_output=c.get("expected_output") or "Expected valid output",
                    failure_reason=None if passed else "Agent hallucinated tool argument or missed required citation",
                    latency_ms=2600.0,
                    tokens_used=2400,
                    cost_usd=0.0024
                ))
            db.commit()

    finally:
        db.close()

    # 5. Run Live Demo Failure Scenarios to emit real spans
    logger.info("Executing Live Demo Agents and Failure Scenarios...")
    from app.ingestion.pipeline import pipeline

    def handle_direct_export(items):
        pipeline.process_spans(items, project_id=settings.DEFAULT_PROJECT_ID, environment="production")

    observe.init(
        endpoint="http://localhost:8000/api/v1/ingest/spans",
        project_id=settings.DEFAULT_PROJECT_ID,
        environment="production",
        capture_prompt_content=True,
        capture_completion_content=True,
        capture_tool_arguments=True,
        capture_tool_results=True,
        direct_handler=handle_direct_export
    )

    # Run all demo agents & failure scenarios
    ScenariosRunner.run_all()
    observe.flush()

    logger.info("Data seeding and scenario generation completed successfully!")

if __name__ == "__main__":
    seed_data()
