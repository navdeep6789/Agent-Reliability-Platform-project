from fastapi import APIRouter
from .v1 import (
    ingestion,
    traces,
    runs,
    agents,
    findings,
    policies,
    evaluations,
    compare,
    pricing,
    metrics,
    system,
    demo,
    projects
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(ingestion.router)
api_router.include_router(traces.router)
api_router.include_router(runs.router)
api_router.include_router(agents.router)
api_router.include_router(findings.router)
api_router.include_router(policies.router)
api_router.include_router(evaluations.router)
api_router.include_router(compare.router)
api_router.include_router(pricing.router)
api_router.include_router(metrics.router)
api_router.include_router(system.router)
api_router.include_router(demo.router)
api_router.include_router(projects.router)
