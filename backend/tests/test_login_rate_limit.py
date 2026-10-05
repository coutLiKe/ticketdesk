from tests.conftest import PASSWORD


def login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_sixth_failed_attempt_is_429_even_with_the_right_password(client, make_user):
    make_user(email="victim@example.com")

    for _ in range(5):
        assert login(client, "victim@example.com", "wrong").status_code == 401

    blocked = login(client, "victim@example.com", PASSWORD)

    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_unknown_emails_are_rate_limited_too(client):
    for _ in range(5):
        login(client, "ghost@example.com", "x")

    assert login(client, "ghost@example.com", "x").status_code == 429


def test_blocking_one_email_does_not_block_another(client, make_user):
    make_user(email="a@example.com")
    make_user(email="b@example.com")
    for _ in range(5):
        login(client, "a@example.com", "wrong")

    assert login(client, "b@example.com", PASSWORD).status_code == 200


def test_successful_login_resets_the_counter(client, make_user):
    make_user(email="user@example.com")
    for _ in range(4):
        login(client, "user@example.com", "wrong")

    assert login(client, "user@example.com", PASSWORD).status_code == 200
    for _ in range(4):
        assert login(client, "user@example.com", "wrong").status_code == 401


def test_per_email_cap_applies_across_different_clients(client, make_user):
    """Spreading guesses over many IPs (simulated by clearing the per-client counter)
    still hits the per-email cap."""
    from app import ratelimit

    make_user(email="target@example.com")
    for _ in range(20):
        login(client, "target@example.com", "wrong")
        ratelimit.per_client.reset()

    assert login(client, "target@example.com", PASSWORD).status_code == 429
