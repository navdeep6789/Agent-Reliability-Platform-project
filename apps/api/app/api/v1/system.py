from fastapi import APIRouter, Depends, Query
from typing import Optional
from ...observability.platform_metrics import platform_metrics
from ...storage.retention import retention_manager
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health")
def healthcheck():
    return {"status": "healthy", "service": "agent-reliability-platform-api"}

@router.get("/observability")
def get_platform_observability():
    """Returns telemetry on the Agent Reliability Platform itself."""
    return platform_metrics.get_metrics()

@router.post("/retention/purge")
def trigger_retention_purge(
    retention_days: Optional[int] = Query(None, ge=1, le=365),
    auth: dict = Depends(verify_api_key)
):
    """Enforces data retention policies by purging records older than retention_days."""
    project_id = auth.get("project_id")
    result = retention_manager.purge_expired_records(
        retention_days=retention_days,
        project_id=project_id
    )
    return result
