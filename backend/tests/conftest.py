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


@pytest.fixture
def make_ticket(db):
    """Factory: make_ticket(requester, assignee=None, status=..., priority=..., title=...)."""
    from app.models import Ticket

    def _make(requester, assignee=None, status=None, priority=None, title="Printer jam", **kw):
        fields = {"title": title, "description": kw.pop("description", "It is stuck")}
        if status is not None:
            fields["status"] = status
        if priority is not None:
            fields["priority"] = priority
        ticket = Ticket(requester=requester, assignee=assignee, **fields)
        db.add(ticket)
        db.flush()
        return ticket

    return _make


@pytest.fixture
def make_comment(db):
    """Factory: make_comment(ticket, author, body=..., is_internal=...)."""
    from app.models import Comment

    def _make(ticket, author, body="a comment", is_internal=False):
        comment = Comment(ticket=ticket, author=author, body=body, is_internal=is_internal)
        db.add(comment)
        db.flush()
        return comment

    return _make


@pytest.fixture
def make_asset(db):
    """Factory: make_asset(tag=..., assigned_to=user, status=..., type=...). Tags auto-increment."""
    from app.models import Asset, AssetStatus, AssetType

    counter = 0

    def _make(tag=None, assigned_to=None, status=None, type=AssetType.LAPTOP, **kw):
        nonlocal counter
        counter += 1
        if status is None:
            status = AssetStatus.ASSIGNED if assigned_to else AssetStatus.IN_STOCK
        asset = Asset(
            asset_tag=tag or f"AST-{counter:04d}",
            name=kw.pop("name", f"Device {counter}"),
            type=type,
            status=status,
            assigned_user=assigned_to,
            **kw,
        )
        db.add(asset)
        db.flush()
        return asset

    return _make


@pytest.fixture(autouse=True)
def reset_login_rate_limits():
    """Failed-login counters live in memory; clear them so tests can't affect each other."""
    from app import ratelimit

    ratelimit.per_client.reset()
    ratelimit.per_email.reset()
    yield
