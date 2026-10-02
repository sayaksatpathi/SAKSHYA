"""
SAKSHYA Database Engine & Session Management

Uses SQLAlchemy with SQLite as the default local database.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from backend.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all SAKSHYA models."""
    pass


# Create engine — SQLite with WAL mode for better concurrency
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.sakshya_debug and settings.sakshya_env == "development",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables defined by Base subclasses."""
    import backend.models  # noqa: F401  — ensure models are imported
    Base.metadata.create_all(bind=engine)
