import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.models import RunModel, SpanModel, ReliabilityFindingModel, PolicyViolationModel
from ...auth.api_keys import verify_api_key
from ...reliability.engine import reliability_engine

router = APIRouter(prefix="/runs", tags=["Runs"])

@router.get("")
def list_runs(
    agent_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id")
    query = db.query(RunModel).filter(RunModel.project_id == project_id)

    if agent_name:
        query = query.filter(RunModel.agent_name == agent_name)
    if status:
        query = query.filter(RunModel.status == status)

    runs = query.order_by(RunModel.start_time.desc()).offset(offset).limit(limit).all()
    
    res = []
    for r in runs:
        res.append({
            "run_id": r.run_id,
            "trace_id": r.trace_id,
            "agent_name": r.agent_name,
            "agent_version": r.agent_version,
            "prompt_version": r.prompt_version,
            "status": r.status,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "end_time": r.end_time.isoformat() if r.end_time else None,
            "duration_ms": r.duration_ms,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "total_tokens": r.total_tokens,
            "cost_usd": r.cost_usd,
            "error_count": r.error_count,
            "retry_count": r.retry_count
        })

    return {"runs": res, "total": len(res)}

@router.get("/{run_id}")
def get_run(
    run_id: str,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    run = db.query(RunModel).filter(RunModel.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    spans_count = db.query(SpanModel).filter(SpanModel.run_id == run_id).count()
    violations_count = db.query(PolicyViolationModel).filter(PolicyViolationModel.run_id == run_id).count()
    findings_count = db.query(ReliabilityFindingModel).filter(ReliabilityFindingModel.run_id == run_id).count()

    return {
        "run_id": run.run_id,
        "trace_id": run.trace_id,
        "project_id": run.project_id,
        "environment": run.environment,
        "agent_name": run.agent_name,
        "agent_version": run.agent_version,
        "prompt_version": run.prompt_version,
        "status": run.status,
        "start_time": run.start_time.isoformat() if run.start_time else None,
        "end_time": run.end_time.isoformat() if run.end_time else None,
        "duration_ms": run.duration_ms,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "total_tokens": run.total_tokens,
        "cost_usd": run.cost_usd,
        "error_count": run.error_count,
        "retry_count": run.retry_count,
        "spans_count": spans_count,
        "violations_count": violations_count,
        "findings_count": findings_count
    }

@router.get("/{run_id}/report")
def get_run_report(
    run_id: str,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    run = db.query(RunModel).filter(RunModel.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    spans = db.query(SpanModel).filter(SpanModel.run_id == run_id).order_by(SpanModel.start_time.asc()).all()
    spans_dicts = []
    for s in spans:
        try:
            a_json = json.loads(s.attributes_json or "{}")
        except Exception:
            a_json = {}
        spans_dicts.append({
            "span_id": s.span_id,
            "parent_span_id": s.parent_span_id,
            "trace_id": s.trace_id,
            "run_id": s.run_id,
            "name": s.name,
            "span_type": s.span_type,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "duration_ms": s.duration_ms,
            "status": s.status,
            "status_message": s.status_message,
            "attributes": a_json
        })

    violations = db.query(PolicyViolationModel).filter(PolicyViolationModel.run_id == run_id).all()
    v_dicts = [{
        "id": v.id,
        "policy_id": v.policy_id,
        "rule_type": v.rule_type,
        "severity": v.severity,
        "threshold_value": v.threshold_value,
        "observed_value": v.observed_value,
        "unit": v.unit,
        "message": v.message
    } for v in violations]

    run_dict = {
        "run_id": run.run_id,
        "trace_id": run.trace_id,
        "agent_name": run.agent_name,
        "duration_ms": run.duration_ms,
        "cost_usd": run.cost_usd,
        "total_tokens": run.total_tokens,
        "error_count": run.error_count,
        "retry_count": run.retry_count
    }

    report = reliability_engine.analyze_run(run_dict, spans_dicts, v_dicts)
    return report.model_dump()
