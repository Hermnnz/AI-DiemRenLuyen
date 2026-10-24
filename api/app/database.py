from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from api.app.config import settings

# SQLite connection args if using sqlite fallback
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine_options = {"connect_args": connect_args, "pool_pre_ping": True}
if settings.IS_PRODUCTION and not settings.DATABASE_URL.startswith("sqlite"):
    # One connection per warm serverless instance; Supabase handles pooling.
    engine_options.update(pool_size=1, max_overflow=0, pool_recycle=300)

engine = create_engine(settings.DATABASE_URL, **engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
