from fastapi import APIRouter
from ...observability.platform_metrics import platform_metrics

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/health")
def healthcheck():
    return {"status": "healthy", "service": "agent-reliability-platform-api"}

@router.get("/observability")
def get_platform_observability():
    """Returns telemetry on the Agent Reliability Platform itself."""
    return platform_metrics.get_metrics()
