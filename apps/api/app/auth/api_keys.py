import hashlib
import secrets
from typing import Optional, Tuple
from fastapi import Header, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..config import settings
from ..storage.database import get_db
from ..storage.models import ApiKeyModel, ProjectModel

security = HTTPBearer(auto_error=False)

def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

def generate_api_key(prefix: str = "arp_live_") -> Tuple[str, str, str]:
    """Returns (raw_key, hashed_key, display_prefix)"""
    secret_part = secrets.token_hex(20)
    raw_key = f"{prefix}{secret_part}"
    hashed = hash_key(raw_key)
    display_prefix = f"{raw_key[:12]}..."
    return raw_key, hashed, display_prefix

def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-Id"),
    x_environment: Optional[str] = Header(None, alias="X-Environment"),
    db: Session = Depends(get_db)
) -> dict:
    raw_key = None
    if credentials:
        raw_key = credentials.credentials
    elif x_api_key:
        raw_key = x_api_key

    project_id = x_project_id or settings.DEFAULT_PROJECT_ID
    environment = x_environment or settings.DEFAULT_ENVIRONMENT

    # In local development mode, allow default access if no key provided
    if not raw_key:
        if settings.ENVIRONMENT == "development":
            return {
                "project_id": project_id,
                "environment": environment,
                "authenticated": True,
                "is_dev": True
            }
        raise HTTPException(status_code=401, detail="API key is required in production")

    # Master API key bypass
    if raw_key == settings.MASTER_API_KEY:
        return {
            "project_id": project_id,
            "environment": environment,
            "authenticated": True,
            "is_master": True
        }

    # Verify against hashed keys
    hashed = hash_key(raw_key)
    key_record = db.query(ApiKeyModel).filter(
        ApiKeyModel.hashed_key == hashed,
        ApiKeyModel.is_active == True
    ).first()

    if not key_record:
        raise HTTPException(status_code=403, detail="Invalid or revoked API key")

    return {
        "project_id": key_record.project_id,
        "environment": key_record.environment,
        "authenticated": True,
        "key_name": key_record.name
    }
