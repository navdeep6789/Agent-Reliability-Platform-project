from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.analytics_duckdb import analytics
from ...auth.api_keys import verify_api_key

router = APIRouter(prefix="/compare", tags=["Comparison"])

@router.get("/models")
def compare_models(
    auth: dict = Depends(verify_api_key)
):
    """Compare performance, token consumption, cost, and latency across actual recorded model spans."""
    project_id = auth.get("project_id", "proj_default_production")
    environment = auth.get("environment", "production")

    comparisons = analytics.get_model_comparisons(project_id, environment)
    return {
        "models": comparisons,
        "total_models": len(comparisons)
    }
