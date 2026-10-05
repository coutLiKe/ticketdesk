from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.cors import add_cors


def make_client(origins: str) -> TestClient:
    app = FastAPI()
    add_cors(app, origins)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return TestClient(app)


def preflight(client, origin):
    return client.options(
        "/ping",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_listed_origin_is_allowed_and_may_send_the_auth_header():
    client = make_client("https://app.example.com")

    response = preflight(client, "https://app.example.com")

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_unlisted_origin_is_not_allowed():
    client = make_client("https://app.example.com")

    response = preflight(client, "https://evil.example.com")

    assert "access-control-allow-origin" not in response.headers


def test_trailing_slashes_and_spaces_in_the_setting_are_tolerated():
    client = make_client(" https://a.example.com/ , https://b.example.com ")

    assert preflight(client, "https://a.example.com").status_code == 200
    assert preflight(client, "https://b.example.com").status_code == 200


def test_empty_setting_adds_no_cors_headers():
    client = make_client("")

    response = client.get("/ping", headers={"Origin": "https://app.example.com"})

    assert "access-control-allow-origin" not in response.headers


def test_credentials_are_not_allowed():
    client = make_client("https://app.example.com")

    assert (
        "access-control-allow-credentials"
        not in preflight(client, "https://app.example.com").headers
    )
