import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    Asset,
    AssetType,
    Comment,
    Priority,
    Role,
    Ticket,
    TicketStatus,
    User,
)


def make_user(email="alice@example.com", role=Role.REQUESTER) -> User:
    return User(email=email, full_name="Alice", hashed_password="x", role=role)


def make_ticket(requester: User, **kwargs) -> Ticket:
    return Ticket(
        title="Laptop won't boot", description="Black screen", requester=requester, **kwargs
    )


def test_user_defaults(db):
    user = make_user()
    db.add(user)
    db.flush()

    assert user.id is not None
    assert user.role == Role.REQUESTER
    assert user.is_active is True
    assert user.created_at is not None


def test_user_email_must_be_unique(db):
    db.add(make_user("dup@example.com"))
    db.flush()

    db.add(make_user("dup@example.com"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_ticket_defaults_to_open_medium_unassigned(db):
    ticket = make_ticket(make_user())
    db.add(ticket)
    db.flush()

    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == Priority.MEDIUM
    assert ticket.assignee is None
    assert ticket.updated_at is not None


def test_ticket_belongs_to_requester_and_assignee(db):
    requester = make_user("req@example.com")
    tech = make_user("tech@example.com", Role.TECHNICIAN)
    ticket = make_ticket(requester, assignee=tech)
    db.add(ticket)
    db.flush()

    assert ticket.requester_id == requester.id
    assert ticket.assignee_id == tech.id


def test_database_rejects_invalid_status_value(db):
    """The CHECK constraint protects the data even if application code is buggy."""
    ticket = make_ticket(make_user())
    db.add(ticket)
    db.flush()

    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE tickets SET status = 'banana' WHERE id = :i"), {"i": ticket.id})


def test_comments_are_ordered_and_deleted_with_ticket(db):
    user = make_user()
    ticket = make_ticket(user)
    ticket.comments = [Comment(author=user, body="first"), Comment(author=user, body="second")]
    db.add(ticket)
    db.flush()
    db.expire_all()

    assert [c.body for c in ticket.comments] == ["first", "second"]

    db.delete(ticket)
    db.flush()
    assert db.scalars(select(Comment)).all() == []


def test_cannot_delete_user_who_has_tickets(db):
    user = make_user()
    db.add(make_ticket(user))
    db.flush()

    with pytest.raises(IntegrityError):
        db.execute(text("DELETE FROM users WHERE id = :i"), {"i": user.id})


def test_deleting_assignee_unassigns_ticket(db):
    requester = make_user("req@example.com")
    tech = make_user("tech@example.com", Role.TECHNICIAN)
    ticket = make_ticket(requester, assignee=tech)
    db.add(ticket)
    db.flush()

    db.execute(text("DELETE FROM users WHERE id = :i"), {"i": tech.id})
    db.expire_all()

    assert ticket.assignee_id is None


def test_asset_tag_must_be_unique(db):
    db.add(Asset(asset_tag="LT-001", name="MacBook", type=AssetType.LAPTOP))
    db.flush()

    db.add(Asset(asset_tag="LT-001", name="Another", type=AssetType.LAPTOP))
    with pytest.raises(IntegrityError):
        db.flush()


def test_ticket_and_asset_many_to_many(db):
    user = make_user()
    laptop = Asset(asset_tag="LT-001", name="MacBook", type=AssetType.LAPTOP)
    monitor = Asset(asset_tag="MN-001", name="Dell 27", type=AssetType.MONITOR)
    ticket = make_ticket(user, assets=[laptop, monitor])
    other_ticket = make_ticket(user, assets=[laptop])
    db.add_all([ticket, other_ticket])
    db.flush()
    db.expire_all()

    assert {a.asset_tag for a in ticket.assets} == {"LT-001", "MN-001"}
    assert len(laptop.tickets) == 2
    assert len(monitor.tickets) == 1


def test_same_asset_cannot_be_linked_to_a_ticket_twice(db):
    user = make_user()
    asset = Asset(asset_tag="LT-001", name="MacBook", type=AssetType.LAPTOP)
    ticket = make_ticket(user, assets=[asset])
    db.add(ticket)
    db.flush()

    with pytest.raises(IntegrityError):
        db.execute(
            text("INSERT INTO ticket_assets (ticket_id, asset_id) VALUES (:t, :a)"),
            {"t": ticket.id, "a": asset.id},
        )
