import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from api.app.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }

engine_options = {"connect_args": connect_args, "pool_pre_ping": True}

is_serverless = bool(os.getenv("VERCEL")) or settings.IS_PRODUCTION
if is_serverless and not settings.DATABASE_URL.startswith("sqlite"):
    engine_options.update(pool_size=5, max_overflow=5, pool_recycle=300)

engine = create_engine(settings.DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
