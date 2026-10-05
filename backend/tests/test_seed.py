from sqlalchemy import func, select

from app.models import Asset, Comment, Role, Ticket, TicketStatus, User
from app.seed import DEMO_PASSWORD, USERS, seed


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_seed_creates_demo_data(db):
    created = seed(db)

    assert created["users"] == len(USERS) == count(db, User)
    assert count(db, Ticket) == created["tickets"] > 0
    assert count(db, Asset) == created["assets"] > 0
    assert count(db, Comment) == created["comments"] > 0


def test_seed_covers_every_role_and_ticket_status(db):
    seed(db)

    assert set(db.scalars(select(User.role))) == set(Role)
    assert set(db.scalars(select(Ticket.status))) == set(TicketStatus)


def test_seed_includes_internal_notes(db):
    seed(db)

    assert db.scalar(select(func.count()).select_from(Comment).where(Comment.is_internal)) > 0


def test_seed_is_idempotent(db):
    seed(db)
    before = {m: count(db, m) for m in (User, Ticket, Comment, Asset)}

    second = seed(db)

    assert second == {"users": 0, "assets": 0, "tickets": 0, "comments": 0}
    assert {m: count(db, m) for m in (User, Ticket, Comment, Asset)} == before


def test_seeded_users_can_log_in(client, db):
    seed(db)

    for email, _, _ in USERS:
        response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
        assert response.status_code == 200, email


def test_seeded_assignments_are_consistent(db):
    """Assets with an assignee are 'assigned'; unassigned ones are never 'assigned'."""
    seed(db)

    for asset in db.scalars(select(Asset)):
        assert (asset.status.value == "assigned") == (asset.assigned_user_id is not None)
