import os

# Must be set BEFORE the app is imported: bcrypt cost 4 keeps password hashing fast in tests.
os.environ.setdefault("BCRYPT_ROUNDS", "4")

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://ticketdesk:ticketdesk@localhost:5432/ticketdesk_test",
)


def alembic_config() -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


def _create_test_database_if_missing() -> None:
    url = make_url(TEST_DATABASE_URL)
    # CREATE DATABASE can't run inside a transaction, hence AUTOCOMMIT.
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    """Build the test schema ONCE per run by running the real migrations.

    Using Alembic (not Base.metadata.create_all) means every test run also proves
    that the migrations produce the schema the models expect.
    """
    _create_test_database_if_missing()
    config = alembic_config()
    command.downgrade(config, "base")  # start clean if a previous run left tables behind
    command.upgrade(config, "head")
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    """A session whose changes are rolled back after each test.

    The session runs inside an outer transaction that we never commit. Even if the code
    under test calls session.commit(), it only releases a SAVEPOINT; the outer rollback
    undoes everything, so tests can't leak data into each other.
    """
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """HTTP test client whose requests use the same rolled-back session as the test."""
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


PASSWORD = "password123"


@pytest.fixture
def make_user(db):
    """Factory: make_user(role=..., email=...) inserts a user and returns it."""
    from app.models import Role, User
    from app.security import hash_password

    counter = 0

    def _make(role=Role.REQUESTER, email=None, is_active=True, password=PASSWORD):
        nonlocal counter
        counter += 1
        user = User(
            email=email or f"user{counter}@example.com",
            full_name=f"User {counter}",
            hashed_password=hash_password(password),
            role=role,
            is_active=is_active,
        )
        db.add(user)
        db.flush()
        return user

    return _make


@pytest.fixture
def auth():
    """auth(user) -> headers dict with a valid Bearer token for that user."""
    from app.security import create_access_token

    def _auth(user):
        return {"Authorization": f"Bearer {create_access_token(user.id)}"}

    return _auth
