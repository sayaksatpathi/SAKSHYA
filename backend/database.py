"""
SAKSHYA Database Engine & Session Management

Uses SQLAlchemy with SQLite as the default local database.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all SAKSHYA models."""
    pass


_is_sqlite = "sqlite" in settings.database_url

# Ensure required storage directories (including the SQLite DB's parent) exist
# before the engine is created. Importing this module is enough to guarantee the
# database file can be opened — important for tests and fresh environments (CI)
# where the storage directory is not checked in.
settings.ensure_directories()

# Create engine. SAKSHYA is a multi-threaded FastAPI app, so when running on
# SQLite we allow cross-thread access and tune the connection for concurrency
# (WAL journaling + a busy timeout) so concurrent readers/writers wait for a
# lock instead of failing with "database is locked".
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30} if _is_sqlite else {},
    echo=settings.sakshya_debug and settings.sakshya_env == "development",
)


if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record):
        """Enable WAL mode and a busy timeout on every SQLite connection."""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
        finally:
            cursor.close()

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
