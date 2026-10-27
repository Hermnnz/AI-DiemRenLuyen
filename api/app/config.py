import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "Web Chấm Điểm Rèn Luyện API"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg2://postgres:postgres@localhost:5432/drl_db"
    )
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production_min_32_chars")
    SESSION_EXPIRE_HOURS: int = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))
    DEMO_PASSWORD: str = os.getenv("DEMO_PASSWORD", "Demo@123456")
    
    # Storage
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", "./storage")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "evidence")
    IS_PRODUCTION: bool = os.getenv("IS_PRODUCTION", "false").lower() == "true"
    CRON_SECRET: str = os.getenv("CRON_SECRET", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    AI_READ_ENABLED: bool = os.getenv("AI_READ_ENABLED", "false").lower() == "true"
    GEMINI_TRANSPARENCY_MODEL: str = os.getenv("GEMINI_TRANSPARENCY_MODEL", "gemini-3.6-flash")
    AI_TRANSPARENCY_ENABLED: bool = os.getenv("AI_TRANSPARENCY_ENABLED", "false").lower() == "true"
    
    # Server & CORS
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


def normalize_database_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


settings = Settings()
settings.DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

if settings.IS_PRODUCTION or os.getenv("VERCEL"):
    if settings.SECRET_KEY.startswith("dev_secret_key_") or len(settings.SECRET_KEY) < 32:
        raise RuntimeError("Production SECRET_KEY is missing or too short")
    if "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL:
        raise RuntimeError("Production DATABASE_URL must use the hosted database")
    db_url = make_url(settings.DATABASE_URL)
    if db_url.host and db_url.host.endswith(".pooler.supabase.com") and "." not in (db_url.username or ""):
        raise RuntimeError("Supabase pooler DATABASE_URL must use the username copied from Supabase Connect")
    if settings.STORAGE_BACKEND != "supabase" or not settings.SUPABASE_SECRET_KEY:
        raise RuntimeError("Production Supabase Storage configuration is missing")
