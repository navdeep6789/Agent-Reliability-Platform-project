from fastapi import APIRouter, Depends, Header, HTTPException, Request
from typing import Dict, Any, List
from ...auth.api_keys import verify_api_key
from ...ingestion.pipeline import pipeline

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

@router.post("/spans")
async def ingest_spans(
    payload: Dict[str, Any],
    auth: dict = Depends(verify_api_key)
):
    """Direct telemetry ingestion endpoint for ARP Python SDK."""
    spans = payload.get("spans", [])
    if not isinstance(spans, list):
        raise HTTPException(status_code=400, detail="Expected 'spans' list in payload")

    project_id = auth.get("project_id", "proj_default_production")
    environment = auth.get("environment", "production")

    result = pipeline.process_spans(spans, project_id=project_id, environment=environment)
    return result

@router.post("/otlp")
async def ingest_otlp(
    payload: Dict[str, Any],
    auth: dict = Depends(verify_api_key)
):
    """Standard OpenTelemetry OTLP/HTTP JSON receiver."""
    project_id = auth.get("project_id", "proj_default_production")
    environment = auth.get("environment", "production")

    result = pipeline.process_otlp_payload(payload, project_id=project_id, environment=environment)
    return result
