import pytest

from app.make_admin import promote_to_admin
from app.models import Role


def test_promotes_an_existing_user_to_admin(db, make_user):
    user = make_user(email="boss@example.com")

    result = promote_to_admin(db, "boss@example.com")

    assert result.id == user.id
    assert result.role == Role.ADMIN


def test_email_match_ignores_case_and_whitespace(db, make_user):
    make_user(email="boss@example.com")

    assert promote_to_admin(db, "  BOSS@Example.com ").role == Role.ADMIN


def test_reactivates_a_deactivated_account(db, make_user):
    make_user(email="boss@example.com", is_active=False)

    assert promote_to_admin(db, "boss@example.com").is_active is True


def test_is_idempotent(db, make_user):
    make_user(email="boss@example.com", role=Role.ADMIN)

    assert promote_to_admin(db, "boss@example.com").role == Role.ADMIN


def test_unknown_email_raises(db):
    with pytest.raises(LookupError):
        promote_to_admin(db, "nobody@example.com")
