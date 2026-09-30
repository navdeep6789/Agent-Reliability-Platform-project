import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.models import SpanModel, RunModel
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/traces", tags=["Traces"])

@router.get("")
def list_traces(
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
    
    results = []
    for r in runs:
        results.append({
            "trace_id": r.trace_id,
            "run_id": r.run_id,
            "agent_name": r.agent_name,
            "agent_version": r.agent_version,
            "status": r.status,
            "start_time": r.start_time.isoformat() if r.start_time else None,
            "duration_ms": r.duration_ms,
            "total_tokens": r.total_tokens,
            "cost_usd": r.cost_usd,
            "error_count": r.error_count,
            "retry_count": r.retry_count
        })

    return {"traces": results, "total": len(results)}

@router.get("/{trace_id}")
def get_trace(
    trace_id: str,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id")
    run = db.query(RunModel).filter(
        RunModel.trace_id == trace_id,
        RunModel.project_id == project_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Trace not found or unauthorized")

    spans = db.query(SpanModel).filter(SpanModel.trace_id == trace_id).order_by(SpanModel.start_time.asc()).all()
    if not spans:
        raise HTTPException(status_code=404, detail="Trace spans not found")

    span_list = []
    for s in spans:
        try:
            attrs = json.loads(s.attributes_json or "{}")
        except Exception:
            attrs = {}
        try:
            events = json.loads(s.events_json or "[]")
        except Exception:
            events = []

        span_list.append({
            "span_id": s.span_id,
            "parent_span_id": s.parent_span_id,
            "trace_id": s.trace_id,
            "run_id": s.run_id,
            "name": s.name,
            "span_type": s.span_type,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "duration_ms": s.duration_ms,
            "status": s.status,
            "status_message": s.status_message,
            "attributes": attrs,
            "events": events
        })

    return {
        "trace_id": trace_id,
        "run": {
            "run_id": run.run_id if run else None,
            "agent_name": run.agent_name if run else "unknown",
            "agent_version": run.agent_version if run else "1.0.0",
            "status": run.status if run else "SUCCESS",
            "duration_ms": run.duration_ms if run else 0.0,
            "cost_usd": run.cost_usd if run else 0.0,
            "total_tokens": run.total_tokens if run else 0
        } if run else None,
        "spans": span_list,
        "total_spans": len(span_list)
    }

@router.get("/{trace_id}/waterfall")
def get_trace_waterfall(
    trace_id: str,
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    project_id = auth.get("project_id")
    run = db.query(RunModel).filter(
        RunModel.trace_id == trace_id,
        RunModel.project_id == project_id
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Trace not found or unauthorized")

    spans = db.query(SpanModel).filter(SpanModel.trace_id == trace_id).order_by(SpanModel.start_time.asc()).all()
    if not spans:
        raise HTTPException(status_code=404, detail="Trace spans not found")

    min_start = min(s.start_time for s in spans)
    max_end = max((s.end_time or s.start_time) for s in spans)
    raw_duration = (max_end - min_start).total_seconds() * 1000.0
    total_trace_duration_ms = max(raw_duration, 1.0)

    # Build span nodes
    nodes: Dict[str, Dict[str, Any]] = {}
    for s in spans:
        start_offset_ms = (s.start_time - min_start).total_seconds() * 1000.0
        dur = s.duration_ms or ((s.end_time - s.start_time).total_seconds() * 1000.0 if s.end_time else 0.0)
        contrib_pct = round((dur / total_trace_duration_ms) * 100.0, 1)

        try:
            attrs = json.loads(s.attributes_json or "{}")
        except Exception:
            attrs = {}

        nodes[s.span_id] = {
            "span_id": s.span_id,
            "parent_span_id": s.parent_span_id,
            "name": s.name,
            "span_type": s.span_type,
            "start_offset_ms": round(start_offset_ms, 2),
            "duration_ms": round(dur, 2),
            "contribution_percent": contrib_pct,
            "status": s.status,
            "status_message": s.status_message,
            "attributes": attrs,
            "children": []
        }

    # Assemble hierarchical tree
    root_nodes = []
    for s_id, node in nodes.items():
        p_id = node["parent_span_id"]
        if p_id and p_id in nodes:
            nodes[p_id]["children"].append(node)
        else:
            root_nodes.append(node)

    return {
        "trace_id": trace_id,
        "total_duration_ms": round(total_trace_duration_ms, 2),
        "root_spans": root_nodes
    }
