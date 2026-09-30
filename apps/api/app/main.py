import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.router import api_router
from .storage.database import init_db, SessionLocal
from .storage.models import ProjectModel, PolicyModel, EvaluationDatasetModel
from .policies.engine import DEFAULT_POLICIES
from .observability.platform_metrics import platform_metrics

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("arp.main")

app = FastAPI(
    title="Agent Reliability Platform API",
    description="Observability, evaluation, debugging, and reliability analysis for LLM applications and AI agents",
    version="1.0.0"
)

# CORS Middleware
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Self-Observability Middleware
@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        elapsed_ms = (time.time() - start) * 1000.0
        platform_metrics.record_query(elapsed_ms)
        return response
    except Exception as e:
        platform_metrics.record_error()
        raise

app.include_router(api_router)

@app.on_event("startup")
def on_startup():
    logger.info("Initializing Agent Reliability Platform database...")
    init_db()
    
    # Seed default project and default policies
    db = SessionLocal()
    try:
        def_proj = db.query(ProjectModel).filter(ProjectModel.id == settings.DEFAULT_PROJECT_ID).first()
        if not def_proj:
            logger.info("Seeding default project...")
            def_proj = ProjectModel(
                id=settings.DEFAULT_PROJECT_ID,
                name="Default Production Project",
                description="Default workspace tenant for Agent Reliability Platform"
            )
            db.add(def_proj)

        # Seed policies
        for p in DEFAULT_POLICIES:
            existing = db.query(PolicyModel).filter(PolicyModel.id == p.id).first()
            if not existing:
                db.add(PolicyModel(
                    id=p.id,
                    project_id=p.project_id,
                    name=p.name,
                    rule_type=p.rule_type,
                    threshold=p.threshold,
                    unit=p.unit,
                    severity=p.severity,
                    enabled=p.enabled,
                    description=p.description
                ))

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error during startup seeding: {e}")
    finally:
        db.close()

    logger.info(f"Agent Reliability Platform API initialized on {settings.HOST}:{settings.PORT}")

@app.get("/")
def root():
    return {
        "service": "Agent Reliability Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "online"
    }
