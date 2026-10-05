from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base
from tests.conftest import alembic_config


def test_migrations_match_models(engine):
    """Fails if someone changes a model but forgets to generate a migration."""
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)

    assert diff == []


def test_migrations_can_downgrade_and_upgrade_again(engine):
    config = alembic_config()

    command.downgrade(config, "base")
    command.upgrade(config, "head")
