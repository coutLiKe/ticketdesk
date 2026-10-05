from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.models import Role


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---- Authentication on a protected endpoint (GET /users/me) --------------------------


def test_me_returns_current_user(client, make_user, auth):
    user = make_user(role=Role.TECHNICIAN)

    response = client.get("/users/me", headers=auth(user))

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["role"] == "technician"


def test_me_without_token_is_401(client):
    response = client.get("/users/me")

    assert response.status_code == 401


@pytest.mark.parametrize("header", ["Bearer garbage", "Basic abc", "Bearer", ""])
def test_me_with_malformed_credentials_is_401(client, header):
    assert client.get("/users/me", headers={"Authorization": header}).status_code == 401


def test_me_with_expired_token_is_401(client, make_user):
    user = make_user()
    claims = {"sub": str(user.id), "exp": datetime.now(UTC) - timedelta(seconds=1)}
    expired = jwt.encode(claims, settings.secret_key, settings.jwt_algorithm)

    assert client.get("/users/me", headers=bearer(expired)).status_code == 401


def test_me_with_token_signed_by_someone_else_is_401(client, make_user):
    user = make_user()
    claims = {"sub": str(user.id), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    forged = jwt.encode(claims, "x" * 32, "HS256")

    assert client.get("/users/me", headers=bearer(forged)).status_code == 401


def test_me_with_token_for_nonexistent_user_is_401(client):
    claims = {"sub": "999999", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = jwt.encode(claims, settings.secret_key, settings.jwt_algorithm)

    assert client.get("/users/me", headers=bearer(token)).status_code == 401


def test_token_stops_working_when_user_is_deactivated(client, make_user, auth):
    user = make_user(is_active=False)

    assert client.get("/users/me", headers=auth(user)).status_code == 401


# ---- GET /users (admin only) ---------------------------------------------------------


def test_admin_can_list_users(client, make_user, auth):
    admin = make_user(role=Role.ADMIN)
    make_user()

    response = client.get("/users", headers=auth(admin))

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all("hashed_password" not in u for u in response.json())


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN])
def test_non_admin_cannot_list_users(client, make_user, auth, role):
    user = make_user(role=role)

    assert client.get("/users", headers=auth(user)).status_code == 403


def test_anonymous_cannot_list_users(client):
    assert client.get("/users").status_code == 401


# ---- PATCH /users/{id} (admin only) --------------------------------------------------


def test_admin_can_change_a_users_role(client, make_user, auth):
    admin = make_user(role=Role.ADMIN)
    target = make_user()

    response = client.patch(f"/users/{target.id}", json={"role": "technician"}, headers=auth(admin))

    assert response.status_code == 200
    assert response.json()["role"] == "technician"


def test_role_change_takes_effect_immediately_for_existing_token(client, make_user, auth):
    admin = make_user(role=Role.ADMIN)
    target = make_user()
    target_headers = auth(target)  # token issued while still a requester
    assert client.get("/users", headers=target_headers).status_code == 403

    client.patch(f"/users/{target.id}", json={"role": "admin"}, headers=auth(admin))

    assert client.get("/users", headers=target_headers).status_code == 200


def test_admin_can_deactivate_a_user_and_their_token_dies(client, make_user, auth):
    admin = make_user(role=Role.ADMIN)
    target = make_user()
    target_headers = auth(target)

    response = client.patch(f"/users/{target.id}", json={"is_active": False}, headers=auth(admin))

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/users/me", headers=target_headers).status_code == 401


@pytest.mark.parametrize("role", [Role.REQUESTER, Role.TECHNICIAN])
def test_non_admin_cannot_modify_users(client, make_user, auth, role):
    user = make_user(role=role)
    target = make_user()

    response = client.patch(f"/users/{target.id}", json={"role": "admin"}, headers=auth(user))

    assert response.status_code == 403


def test_requester_cannot_promote_themselves(client, make_user, auth):
    user = make_user()

    response = client.patch(f"/users/{user.id}", json={"role": "admin"}, headers=auth(user))

    assert response.status_code == 403


def test_anonymous_cannot_modify_users(client, make_user):
    target = make_user()

    assert client.patch(f"/users/{target.id}", json={"role": "admin"}).status_code == 401


def test_patch_unknown_user_is_404(client, make_user, auth):
    admin = make_user(role=Role.ADMIN)

    assert (
        client.patch("/users/999999", json={"role": "admin"}, headers=auth(admin)).status_code
        == 404
    )


def test_patch_with_invalid_role_is_422(client, make_user, auth):
    admin = make_user(role=Role.ADMIN)
    target = make_user()

    response = client.patch(f"/users/{target.id}", json={"role": "emperor"}, headers=auth(admin))

    assert response.status_code == 422


def test_patch_with_empty_body_is_422(client, make_user, auth):
    admin = make_user(role=Role.ADMIN)
    target = make_user()

    assert client.patch(f"/users/{target.id}", json={}, headers=auth(admin)).status_code == 422


def test_admin_cannot_demote_or_deactivate_themselves(client, make_user, auth):
    """Prevents locking everyone out by accident."""
    admin = make_user(role=Role.ADMIN)

    demote = client.patch(f"/users/{admin.id}", json={"role": "requester"}, headers=auth(admin))
    deactivate = client.patch(f"/users/{admin.id}", json={"is_active": False}, headers=auth(admin))

    assert demote.status_code == 409
    assert deactivate.status_code == 409


# ---- GET /users/directory (staff only) -----------------------------------------------


@pytest.mark.parametrize("role", [Role.TECHNICIAN, Role.ADMIN])
def test_staff_can_see_the_user_directory_without_emails(client, make_user, auth, role):
    me = make_user(role=role)
    requester = make_user()
    make_user(is_active=False)

    response = client.get("/users/directory", headers=auth(me))

    assert response.status_code == 200
    assert {u["id"] for u in response.json()} == {me.id, requester.id}
    assert all(set(u) == {"id", "full_name", "role"} for u in response.json())


def test_requester_cannot_see_the_user_directory(client, make_user, auth):
    assert client.get("/users/directory", headers=auth(make_user())).status_code == 403


def test_directory_requires_login(client):
    assert client.get("/users/directory").status_code == 401
