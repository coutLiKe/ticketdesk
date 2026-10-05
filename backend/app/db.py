from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# One engine per process: it owns the connection pool.
# pool_pre_ping tests a connection before use, so a restarted DB doesn't cause one failed request.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# A session is a short-lived "unit of work": one per request.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


# Predictable constraint names. Without them Postgres invents names, and Alembic can't
# reliably drop or alter a constraint it can't name.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Parent class of every model. Collects table definitions in Base.metadata."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: give each request its own session and always close it."""
    with SessionLocal() as session:
        yield session
