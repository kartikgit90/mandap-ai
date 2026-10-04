"""Claude connector: cost maths, and the admin test endpoint (with a fake Claude)."""

import pytest
from fastapi.testclient import TestClient

import app.auth as auth
from app import llm
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_firebase(monkeypatch):
    tokens = {
        "couple-token": {"uid": "u1"},
        "admin-token": {"uid": "u2", "role": "admin"},
    }

    def fake_verify(t):
        if t not in tokens:
            raise ValueError("bad token")
        return tokens[t]

    monkeypatch.setattr(auth, "verify_token", fake_verify)


def test_cost_maths():
    # 1M input + 1M output tokens on Haiku = $1 + $5 = $6 = Rs 510 at 85
    assert llm.cost_inr("fast", 1_000_000, 1_000_000) == 510.0
    # A typical tiny call: 50 in, 30 out on Haiku
    assert llm.cost_inr("fast", 50, 30) == round((50 / 1e6 * 1 + 30 / 1e6 * 5) * 85, 4)


def test_llm_test_needs_admin():
    r = client.post("/admin/llm-test", headers={"Authorization": "Bearer couple-token"})
    assert r.status_code == 403


def test_llm_test_returns_reply_and_cost(monkeypatch):
    monkeypatch.setattr(
        llm,
        "ask",
        lambda *a, **k: llm.LLMResult("Book mehendi artists early.", "claude-haiku-4-5", 40, 10, 0.0076, 900),
    )
    r = client.post("/admin/llm-test", headers={"Authorization": "Bearer admin-token"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "Book mehendi artists early."
    assert body["cost_inr"] == 0.0076


def test_llm_failure_is_reported(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    monkeypatch.setattr(llm, "ask", boom)
    r = client.post("/admin/llm-test", headers={"Authorization": "Bearer admin-token"})
    assert r.status_code == 502
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]
