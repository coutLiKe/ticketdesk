from app.models import Role, User
from tests.conftest import PASSWORD

REGISTER = {"email": "new@example.com", "full_name": "New User", "password": PASSWORD}


# ---- POST /auth/register -------------------------------------------------------------


def test_register_creates_requester_and_hides_password(client, db):
    response = client.post("/auth/register", json=REGISTER)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["role"] == "requester"
    assert "password" not in body and "hashed_password" not in body
    stored = db.query(User).filter_by(email="new@example.com").one()
    assert stored.hashed_password != PASSWORD


def test_register_ignores_a_role_sent_by_the_client(client):
    """Privilege escalation attempt: signup must always produce a requester."""
    response = client.post("/auth/register", json={**REGISTER, "role": "admin"})

    assert response.status_code == 201
    assert response.json()["role"] == "requester"


def test_register_duplicate_email_is_409_case_insensitive(client, make_user):
    make_user(email="taken@example.com")

    response = client.post("/auth/register", json={**REGISTER, "email": "TAKEN@example.com"})

    assert response.status_code == 409


def test_register_stores_email_lowercased(client):
    response = client.post("/auth/register", json={**REGISTER, "email": "MiXed@Example.com"})

    assert response.json()["email"] == "mixed@example.com"


def test_register_rejects_invalid_email(client):
    assert client.post("/auth/register", json={**REGISTER, "email": "nope"}).status_code == 422


def test_register_rejects_short_password(client):
    assert client.post("/auth/register", json={**REGISTER, "password": "short"}).status_code == 422


def test_register_rejects_password_over_bcrypt_limit(client):
    """bcrypt only uses the first 72 bytes, so longer passwords are refused up front."""
    assert client.post("/auth/register", json={**REGISTER, "password": "a" * 73}).status_code == 422


# ---- POST /auth/login ----------------------------------------------------------------


def test_login_returns_a_working_token(client, make_user):
    user = make_user(email="login@example.com")

    response = client.post("/auth/login", json={"email": "login@example.com", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    me = client.get("/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["id"] == user.id


def test_login_email_is_case_insensitive(client, make_user):
    make_user(email="login@example.com")

    response = client.post("/auth/login", json={"email": "LOGIN@example.com", "password": PASSWORD})

    assert response.status_code == 200


def test_login_wrong_password_is_401(client, make_user):
    make_user(email="login@example.com")

    response = client.post("/auth/login", json={"email": "login@example.com", "password": "wrong"})

    assert response.status_code == 401


def test_login_unknown_email_gives_same_error_as_wrong_password(client, make_user):
    """Same status and message either way, so attackers can't discover which emails exist."""
    make_user(email="login@example.com")

    wrong_password = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "wrong"}
    )
    unknown_email = client.post("/auth/login", json={"email": "ghost@example.com", "password": "x"})

    assert unknown_email.status_code == wrong_password.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_deactivated_user_cannot_log_in(client, make_user):
    make_user(email="gone@example.com", is_active=False)

    response = client.post("/auth/login", json={"email": "gone@example.com", "password": PASSWORD})

    assert response.status_code == 401


def test_login_missing_fields_is_422(client):
    assert client.post("/auth/login", json={"email": "a@example.com"}).status_code == 422


def test_role_enum_values():
    assert {r.value for r in Role} == {"requester", "technician", "admin"}
