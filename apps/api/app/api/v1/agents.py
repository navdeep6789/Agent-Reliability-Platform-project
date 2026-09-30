from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.models import AgentModel, RunModel, ReliabilityFindingModel
from ...storage.analytics_duckdb import analytics
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("")
def list_agents(
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id", "proj_default_production")
    environment = auth.get("environment", "production")

    # Get aggregate analytics from DuckDB
    health_metrics = analytics.get_agent_health(project_id, environment)
    
    # Also fetch all known agents in DB
    db_agents = db.query(AgentModel).filter(AgentModel.project_id == project_id).all()
    health_map = {h["agent_name"]: h for h in health_metrics}

    agents_list = []
    # Combine registered agents
    for a in db_agents:
        m = health_map.get(a.name, {
            "agent_name": a.name,
            "total_runs": 0,
            "success_count": 0,
            "error_count": 0,
            "error_rate": 0.0,
            "success_rate": 100.0,
            "avg_duration_ms": 0.0,
            "p95_duration_ms": 0.0,
            "avg_cost_usd": 0.0,
            "total_tokens": 0,
            "total_retries": 0
        })
        agents_list.append({
            "id": a.id,
            "name": a.name,
            "description": a.description,
            **m
        })

    # If any agents recorded in duckdb that weren't in AgentModel yet
    for h in health_metrics:
        if not any(al["name"] == h["agent_name"] for al in agents_list):
            agents_list.append({
                "id": f"agent_{h['agent_name']}",
                "name": h["agent_name"],
                "description": f"Agent {h['agent_name']}",
                **h
            })

    return {"agents": agents_list, "total": len(agents_list)}

@router.get("/{agent_name}")
def get_agent_detail(
    agent_name: str,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id", "proj_default_production")
    environment = auth.get("environment", "production")

    health_metrics = analytics.get_agent_health(project_id, environment)
    agent_stat = next((h for h in health_metrics if h["agent_name"] == agent_name), None)

    recent_runs = db.query(RunModel).filter(
        RunModel.project_id == project_id,
        RunModel.agent_name == agent_name
    ).order_by(RunModel.start_time.desc()).limit(10).all()

    recent_findings = db.query(ReliabilityFindingModel).join(
        RunModel, ReliabilityFindingModel.run_id == RunModel.run_id
    ).filter(
        RunModel.agent_name == agent_name,
        RunModel.project_id == project_id,
        ReliabilityFindingModel.project_id == project_id
    ).order_by(ReliabilityFindingModel.created_at.desc()).limit(10).all()

    return {
        "agent_name": agent_name,
        "metrics": agent_stat or {
            "total_runs": len(recent_runs),
            "p95_duration_ms": 0.0,
            "avg_cost_usd": 0.0,
            "error_rate": 0.0
        },
        "recent_runs": [{
            "run_id": r.run_id,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "cost_usd": r.cost_usd,
            "error_count": r.error_count,
            "retry_count": r.retry_count,
            "start_time": r.start_time.isoformat() if r.start_time else None
        } for r in recent_runs],
        "recent_findings": [{
            "id": f.id,
            "run_id": f.run_id,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "title": f.title,
            "target_entity": f.target_entity,
            "observed_metric": f.observed_metric
        } for f in recent_findings]
    }
