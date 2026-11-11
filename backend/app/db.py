from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
import time

from app.config import settings
from app.models import Base


def _prepare_sqlite(url: str) -> None:
    if not url.startswith("sqlite") or url.endswith(":memory:"):
        return
    raw = url.split("sqlite:///", 1)[-1]
    if not raw or raw.startswith(":memory:"):
        return
    Path(raw).parent.mkdir(parents=True, exist_ok=True)


_prepare_sqlite(settings.database_url)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    pool_pre_ping=not settings.database_url.startswith("sqlite"),
    future=True,
    connect_args=connect_args,
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create tables.

    SQLite tries once so a missing Postgres install does not block startup.
    Postgres retries while the Docker database is still coming up.
    """
    _prepare_sqlite(settings.database_url)
    attempts = 1 if settings.using_sqlite else 20
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            if settings.database_url.startswith("postgresql"):
                with engine.connect() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()
            Base.metadata.create_all(bind=engine)
            _migrate_sqlite()
            return
        except Exception as exc:
            last = exc
            if attempt + 1 < attempts:
                time.sleep(1)
    raise last or RuntimeError("Could not initialize database")


def _migrate_sqlite() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text("PRAGMA table_info(documents)")).fetchall()]
        if "insights" not in cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN insights JSON"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
