from alembic import context
from sqlalchemy import create_engine

from app import models  # noqa: F401  (importing registers the tables on Base.metadata)
from app.config import settings
from app.db import Base

config = context.config
target_metadata = Base.metadata


def run_migrations_online() -> None:
    # Tests set sqlalchemy.url to point at the test database; otherwise use app settings.
    url = config.get_main_option("sqlalchemy.url") or settings.database_url
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # also detect column type changes when autogenerating
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
