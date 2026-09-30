from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from ...storage.database import get_db
from ...storage.models import ProjectModel, ApiKeyModel
from ...auth.api_keys import generate_api_key, verify_api_key

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("")
def list_projects(
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    projects = db.query(ProjectModel).all()
    return {
        "projects": [{
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in projects]
    }

@router.post("")
def create_project(
    payload: Dict[str, Any] = Body(...),
    auth: dict = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    p_id = payload.get("id") or f"proj_{payload.get('name', 'project').lower().replace(' ', '_')}"
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Project name is required")

    existing = db.query(ProjectModel).filter(ProjectModel.id == p_id).first()
    if existing:
        return {"id": existing.id, "name": existing.name}

    proj = ProjectModel(
        id=p_id,
        name=name,
        description=payload.get("description", "")
    )
    db.add(proj)

    # Generate initial ingestion API key for this project
    raw_key, hashed_key, prefix = generate_api_key()
    api_key_rec = ApiKeyModel(
        id=f"key_{p_id[:8]}",
        project_id=p_id,
        environment="production",
        name=f"Default Production Key",
        hashed_key=hashed_key,
        prefix=prefix
    )
    db.add(api_key_rec)
    db.commit()

    return {
        "id": proj.id,
        "name": proj.name,
        "api_key": raw_key, # Returned ONLY ONCE upon creation!
        "note": "Save this API key; it will not be shown again."
    }
