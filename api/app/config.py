import os
from pydantic_settings import BaseSettings, SettingsConfigDict
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
    
    # Auto-route Supabase direct host (which is IPv6 only) to IPv4 pooler
    import urllib.parse
    parsed = urllib.parse.urlsplit(url)
    hostname = parsed.hostname or ""
    if hostname.startswith("db.") and hostname.endswith(".supabase.co"):
        ref = hostname.split(".")[1]
        user = parsed.username or "postgres"
        if "." not in user:
            user = f"{user}.{ref}"
        password = parsed.password or ""
        new_netloc = f"{user}:{password}@aws-0-ap-southeast-1.pooler.supabase.com:6543"
        url = urllib.parse.urlunsplit((parsed.scheme, new_netloc, parsed.path, parsed.query, parsed.fragment))
    return url


settings = Settings()
settings.DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

if settings.IS_PRODUCTION:
    if settings.SECRET_KEY.startswith("dev_secret_key_") or len(settings.SECRET_KEY) < 32:
        raise RuntimeError("Production SECRET_KEY is missing or too short")
    if "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL:
        raise RuntimeError("Production DATABASE_URL must use the hosted database")
    if settings.STORAGE_BACKEND != "supabase" or not settings.SUPABASE_SECRET_KEY:
        raise RuntimeError("Production Supabase Storage configuration is missing")
