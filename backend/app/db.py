from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# One engine per process: it owns the connection pool.
# pool_pre_ping tests a connection before use, so a restarted DB doesn't cause one failed request.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# A session is a short-lived "unit of work": one per request.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class of every model. Collects table definitions in Base.metadata."""


def get_db() -> Iterator[Session]:
    """FastAPI dependency: give each request its own session and always close it."""
    with SessionLocal() as session:
        yield session
