import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
_schema_ready = False


def ensure_schema() -> None:
    # Same non-destructive create_all as migration 0001; needed because serverless deploys cannot run Alembic.
    global _schema_ready
    if _schema_ready:
        return
    from app.domain import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        _schema_ready = True
    except Exception:
        logger.exception("Database schema initialization failed")


def get_db() -> Generator[Session, None, None]:
    ensure_schema()
    with SessionLocal() as session:
        yield session
