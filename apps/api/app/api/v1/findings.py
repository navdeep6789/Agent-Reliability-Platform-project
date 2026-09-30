import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.models import ReliabilityFindingModel, RunModel
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/findings", tags=["Findings"])

@router.get("")
def list_findings(
    finding_type: Optional[str] = None,
    severity: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id", "proj_default_production")
    query = db.query(ReliabilityFindingModel)

    if finding_type:
        query = query.filter(ReliabilityFindingModel.finding_type == finding_type)
    if severity:
        query = query.filter(ReliabilityFindingModel.severity == severity)
    if agent_name:
        query = query.join(RunModel, ReliabilityFindingModel.run_id == RunModel.run_id).filter(RunModel.agent_name == agent_name)

    findings = query.order_by(ReliabilityFindingModel.created_at.desc()).limit(limit).all()

    results = []
    for f in findings:
        try:
            details = json.loads(f.details_json or "{}")
        except Exception:
            details = {}
        try:
            actions = json.loads(f.suggested_actions_json or "[]")
        except Exception:
            actions = []

        results.append({
            "id": f.id,
            "run_id": f.run_id,
            "trace_id": f.trace_id,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "title": f.title,
            "description": f.description,
            "target_entity": f.target_entity,
            "observed_metric": f.observed_metric,
            "contribution_percent": f.contribution_percent,
            "details": details,
            "suggested_actions": actions,
            "created_at": f.created_at.isoformat() if f.created_at else None
        })

    return {"findings": results, "total": len(results)}
