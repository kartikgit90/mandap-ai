"""Basic checks: health works, login is required, and roles are enforced.

We swap the real Firebase token check for a fake one, so tests run without the internet.
"""

import pytest
from fastapi.testclient import TestClient

import app.auth as auth
from app.main import app

client = TestClient(app)

FAKE_TOKENS = {
    "couple-token": {"uid": "u1", "email": "couple@example.com"},
    "admin-token": {"uid": "u2", "email": "admin@example.com", "role": "admin"},
}


@pytest.fixture(autouse=True)
def fake_firebase(monkeypatch):
    def fake_verify(token: str) -> dict:
        if token not in FAKE_TOKENS:
            raise ValueError("bad token")
        return FAKE_TOKENS[token]

    monkeypatch.setattr(auth, "verify_token", fake_verify)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health_is_public():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "x-trace-id" in r.headers


def test_me_needs_login():
    assert client.get("/me").status_code == 401


def test_bad_token_rejected():
    assert client.get("/me", headers=bearer("nope")).status_code == 401


def test_default_role_is_couple():
    r = client.get("/me", headers=bearer("couple-token"))
    assert r.status_code == 200
    assert r.json()["role"] == "couple"


def test_couple_cannot_reach_admin():
    assert client.get("/admin/ping", headers=bearer("couple-token")).status_code == 403


@pytest.mark.parametrize(
    "origin,allowed",
    [
        ("https://mandap-web--mandap-ai.asia-southeast1.hosted.app", True),
        ("http://localhost:3000", True),
        ("https://evil.example.com", False),
        ("https://mandap-web--someone-else.us-central1.hosted.app", False),
    ],
)
def test_cors_allows_only_our_sites(origin, allowed):
    r = client.options(
        "/me",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    assert (r.headers.get("access-control-allow-origin") == origin) is allowed


def test_admin_can_reach_admin():
    assert client.get("/admin/ping", headers=bearer("admin-token")).status_code == 200
