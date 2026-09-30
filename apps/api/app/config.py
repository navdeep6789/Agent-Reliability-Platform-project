import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Agent Reliability Platform API"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    DEFAULT_PROJECT_ID: str = os.getenv("DEFAULT_PROJECT_ID", "proj_default_production")
    DEFAULT_ENVIRONMENT: str = os.getenv("DEFAULT_ENVIRONMENT", "production")
    MASTER_API_KEY: str = os.getenv("MASTER_API_KEY", "arp_live_master_secret_key_change_in_production")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001")

    ROOT_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

    # Dual Storage: Relational (SQLite / Postgres) + Analytical (DuckDB / ClickHouse)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')), 'arp_metadata.db').replace(os.sep, '/')}")
    DUCKDB_PATH: str = os.getenv("DUCKDB_PATH", os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')), 'arp_telemetry.duckdb'))

    CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST", "")
    CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", "9000"))
    CLICKHOUSE_DB: str = os.getenv("CLICKHOUSE_DB", "arp_analytics")

    # Retention
    TRACE_RETENTION_DAYS: int = int(os.getenv("TRACE_RETENTION_DAYS", "30"))
    EVENT_RETENTION_DAYS: int = int(os.getenv("EVENT_RETENTION_DAYS", "30"))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
