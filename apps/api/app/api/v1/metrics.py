from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends
from ...storage.analytics_duckdb import analytics
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/timeseries")
def get_timeseries_metrics(
    auth: dict = Depends(verify_api_key)
):
    project_id = auth.get("project_id", "proj_default_production")
    environment = auth.get("environment", "production")

    points = analytics.get_timeseries_metrics(project_id, environment)
    return {
        "points": points,
        "total_points": len(points)
    }
