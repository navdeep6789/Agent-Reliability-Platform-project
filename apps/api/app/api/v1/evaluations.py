import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.models import EvaluationDatasetModel, EvaluationRunModel, EvaluationCaseResultModel
from ...evaluations.regressions import RegressionAnalyzer
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])

@router.get("/datasets")
def list_datasets(
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id", "proj_default_production")
    datasets = db.query(EvaluationDatasetModel).filter(EvaluationDatasetModel.project_id == project_id).all()
    
    return {
        "datasets": [{
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "agent_target": d.agent_target,
            "version": d.version,
            "total_cases": d.total_cases,
            "created_at": d.created_at.isoformat() if d.created_at else None
        } for d in datasets]
    }

@router.get("/runs")
def list_eval_runs(
    agent_name: Optional[str] = None,
    limit: int = 50,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id", "proj_default_production")
    query = db.query(EvaluationRunModel).filter(EvaluationRunModel.project_id == project_id)
    if agent_name:
        query = query.filter(EvaluationRunModel.agent_name == agent_name)

    runs = query.order_by(EvaluationRunModel.created_at.desc()).limit(limit).all()

    return {
        "runs": [{
            "id": r.id,
            "dataset_id": r.dataset_id,
            "dataset_name": r.dataset_name,
            "agent_name": r.agent_name,
            "agent_version": r.agent_version,
            "prompt_version": r.prompt_version,
            "total_cases": r.total_cases,
            "passed_cases": r.passed_cases,
            "failed_cases": r.failed_cases,
            "pass_rate": r.pass_rate,
            "average_score": r.average_score,
            "average_latency_ms": r.average_latency_ms,
            "total_cost_usd": r.total_cost_usd,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in runs]
    }

@router.get("/runs/{eval_run_id}")
def get_eval_run_detail(
    eval_run_id: str,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id", "proj_default_production")
    run = db.query(EvaluationRunModel).filter(
        EvaluationRunModel.id == eval_run_id,
        EvaluationRunModel.project_id == project_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found or unauthorized")

    cases = db.query(EvaluationCaseResultModel).filter(
        EvaluationCaseResultModel.eval_run_id == eval_run_id
    ).all()

    try:
        failures = json.loads(run.failure_breakdown_json or "{}")
    except Exception:
        failures = {}

    return {
        "run": {
            "id": run.id,
            "dataset_name": run.dataset_name,
            "agent_name": run.agent_name,
            "agent_version": run.agent_version,
            "prompt_version": run.prompt_version,
            "total_cases": run.total_cases,
            "passed_cases": run.passed_cases,
            "failed_cases": run.failed_cases,
            "pass_rate": run.pass_rate,
            "average_score": run.average_score,
            "average_latency_ms": run.average_latency_ms,
            "total_cost_usd": run.total_cost_usd,
            "failure_breakdown": failures,
            "created_at": run.created_at.isoformat() if run.created_at else None
        },
        "cases": [{
            "id": c.id,
            "case_id": c.case_id,
            "case_name": c.case_name,
            "passed": c.passed,
            "score": c.score,
            "evaluator_type": c.evaluator_type,
            "actual_output": c.actual_output,
            "expected_output": c.expected_output,
            "failure_reason": c.failure_reason,
            "latency_ms": c.latency_ms,
            "tokens_used": c.tokens_used,
            "cost_usd": c.cost_usd
        } for c in cases]
    }

@router.post("/compare")
def compare_evaluation_runs(
    payload: Dict[str, Any] = Body(...),
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    baseline_id = payload.get("baseline_run_id")
    candidate_id = payload.get("candidate_run_id")

    if not baseline_id or not candidate_id:
        raise HTTPException(status_code=400, detail="baseline_run_id and candidate_run_id are required")

    b_run = db.query(EvaluationRunModel).filter(EvaluationRunModel.id == baseline_id).first()
    c_run = db.query(EvaluationRunModel).filter(EvaluationRunModel.id == candidate_id).first()

    if not b_run or not c_run:
        raise HTTPException(status_code=404, detail="One or both evaluation runs not found")

    b_dict = {
        "id": b_run.id,
        "agent_name": b_run.agent_name,
        "agent_version": b_run.agent_version,
        "pass_rate": b_run.pass_rate,
        "average_score": b_run.average_score,
        "average_latency_ms": b_run.average_latency_ms,
        "total_cost_usd": b_run.total_cost_usd
    }

    c_dict = {
        "id": c_run.id,
        "agent_name": c_run.agent_name,
        "agent_version": c_run.agent_version,
        "pass_rate": c_run.pass_rate,
        "average_score": c_run.average_score,
        "average_latency_ms": c_run.average_latency_ms,
        "total_cost_usd": c_run.total_cost_usd
    }

    report = RegressionAnalyzer.compare_runs(b_dict, c_dict)
    return report.model_dump()
