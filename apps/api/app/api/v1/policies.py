from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.models import PolicyViolationModel, PolicyModel
from ...policies.engine import policy_engine
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/policies", tags=["Policies"])

@router.get("")
def list_policies(
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    policies = policy_engine.list_policies()
    
    # Calculate violation counts for each policy
    results = []
    for p in policies:
        v_count = db.query(PolicyViolationModel).filter(PolicyViolationModel.rule_type == p.rule_type).count()
        results.append({
            "id": p.id,
            "name": p.name,
            "rule_type": p.rule_type,
            "threshold": p.threshold,
            "unit": p.unit,
            "severity": p.severity,
            "enabled": p.enabled,
            "description": p.description,
            "violation_count": v_count
        })

    return {"policies": results, "total": len(results)}

@router.put("/{policy_id}")
def update_policy(
    policy_id: str,
    payload: Dict[str, Any] = Body(...),
    auth: dict = Depends(verify_api_key)
):
    enabled = payload.get("enabled")
    threshold = payload.get("threshold")

    updated = policy_engine.update_policy(policy_id, enabled=enabled, threshold=threshold)
    if not updated:
        raise HTTPException(status_code=404, detail="Policy not found")

    return updated.model_dump()

@router.get("/violations")
def list_violations(
    rule_type: Optional[str] = None,
    limit: int = 50,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    query = db.query(PolicyViolationModel)
    if rule_type:
        query = query.filter(PolicyViolationModel.rule_type == rule_type)

    violations = query.order_by(PolicyViolationModel.created_at.desc()).limit(limit).all()

    return {
        "violations": [{
            "id": v.id,
            "run_id": v.run_id,
            "trace_id": v.trace_id,
            "policy_id": v.policy_id,
            "rule_type": v.rule_type,
            "severity": v.severity,
            "threshold_value": v.threshold_value,
            "observed_value": v.observed_value,
            "unit": v.unit,
            "message": v.message,
            "created_at": v.created_at.isoformat() if v.created_at else None
        } for v in violations],
        "total": len(violations)
    }
