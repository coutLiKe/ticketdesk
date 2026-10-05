from tests.conftest import PASSWORD


def register(client, n):
    return client.post(
        "/auth/register",
        json={"email": f"person{n}@example.com", "full_name": f"Person {n}", "password": PASSWORD},
    )


def test_eleventh_signup_from_one_address_is_429(client):
    for n in range(10):
        assert register(client, n).status_code == 201

    blocked = register(client, 10)

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_failed_signups_count_too(client, make_user):
    """Duplicate-email attempts (409) use up the allowance like successful ones."""
    make_user(email="taken@example.com")
    for _ in range(10):
        client.post(
            "/auth/register",
            json={"email": "taken@example.com", "full_name": "X", "password": PASSWORD},
        )

    assert register(client, 99).status_code == 429


def test_blocked_signup_does_not_create_a_user(client, db):
    from sqlalchemy import func, select

    from app.models import User

    for n in range(10):
        register(client, n)
    register(client, 10)

    assert db.scalar(select(func.count()).select_from(User)) == 10
