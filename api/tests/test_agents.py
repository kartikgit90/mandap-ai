"""Agents with a scripted fake Claude: checks tools, cards, approval gates and limits."""

from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

import app.auth as auth
from app import llm
from app.main import app
from app.store import store

client = TestClient(app)
H = {"Authorization": "Bearer couple-token"}


@pytest.fixture(autouse=True)
def fake_firebase(monkeypatch):
    monkeypatch.setattr(auth, "verify_token", lambda t: {"uid": "couple-1"} if t == "couple-token" else (_ for _ in ()).throw(ValueError()))
    store().docs.clear()


def block_text(t):
    return NS(type="text", text=t, model_dump=lambda: {"type": "text", "text": t})


def block_tool(i, name, inp):
    return NS(type="tool_use", id=i, name=name, input=inp,
              model_dump=lambda: {"type": "tool_use", "id": i, "name": name, "input": inp})


def resp(blocks, stop):
    return NS(content=blocks, stop_reason=stop, model="fake-haiku", usage=NS(input_tokens=100, output_tokens=20))


class FakeClaude:
    """Replays a script of responses and records what it was sent."""

    def __init__(self, script):
        self.script, self.sent = list(script), []
        self.messages = NS(create=self.create)

    def create(self, **kw):
        self.sent.append(kw)
        return self.script.pop(0)


def use(monkeypatch, script):
    fake = FakeClaude(script)
    monkeypatch.setattr(llm, "_client", lambda: fake)
    return fake


def test_stylist_builds_look_and_drafts_enquiry(monkeypatch):
    fake = use(monkeypatch, [
        resp([block_tool("t1", "search_catalog", {"function": "sangeet", "side": "bride", "colors": ["emerald"]})], "tool_use"),
        resp([block_tool("t2", "propose_look", {"title": "Emerald dance-floor look", "function": "sangeet", "side": "bride",
                                                "product_ids": ["p01", "p09", "p14"], "why": "Light and sparkly", "top_pick": True}),
              block_tool("t3", "draft_enquiry", {"product_ids": ["p01"], "questions": ["Ready by 10 Jan 2027?"]})], "tool_use"),
        resp([block_text("Here is your look. Review the enquiry and press Send.")], "end_turn"),
    ])
    r = client.post("/stylist/chat", headers=H, json={
        "messages": [{"role": "user", "content": "Emerald sangeet look under 2.5 lakh"}],
        "context": {"function": "sangeet", "side": "bride", "budget": 250000}})
    assert r.status_code == 200, r.text
    body = r.json()
    look = body["events"]["looks"][0]
    assert look["total"] == 160000 + 55000 + 18000 and look["within_budget"]
    draft = body["events"]["drafts"][0]
    assert draft["status"] == "draft" and draft["brand"] == "Atelier Noor"
    assert {"tier": "verified", "title": "Brand catalogue"} in body["events"]["sources"]
    # The tool results Claude saw never contained confidential contact details
    assert "example-noor.test" not in str(fake.sent)

    # Nothing is sent until the couple approves
    assert client.get("/enquiries", headers=H).json()[0]["status"] == "draft"
    sent = client.post(f'/enquiries/{draft["id"]}/send', headers=H).json()
    assert sent["status"] == "sent"


def test_stylist_rejects_made_up_products(monkeypatch):
    use(monkeypatch, [
        resp([block_tool("t1", "propose_look", {"title": "Fake", "function": "sangeet", "side": "bride",
                                                "product_ids": ["p999", "p01"], "why": "x"})], "tool_use"),
        resp([block_text("Sorry, let me search first.")], "end_turn"),
    ])
    body = client.post("/stylist/chat", headers=H, json={"messages": [{"role": "user", "content": "look"}]}).json()
    assert body["events"]["looks"] == []


def test_saved_look_is_repriced_from_catalogue():
    r = client.post("/looks", headers=H, json={"look": {"title": "Mine", "function": "sangeet", "side": "bride",
                                                         "pieces": [{"id": "p01", "price": 1}, {"id": "p09", "price": 1}]}})
    assert r.status_code == 200 and r.json()["total"] == 215000


def test_destination_estimates_and_proposal_needs_apply(monkeypatch):
    use(monkeypatch, [
        resp([block_tool("t1", "estimate_budget", {"destination_id": "udaipur"}),
              block_tool("t2", "set_shortlist", {"destination_ids": ["udaipur", "jaipur"]})], "tool_use"),
        resp([block_tool("t3", "propose_plan_change", {"destination_id": "udaipur", "overrides": {"decor": 500000},
                                                       "summary": "Sangeet on the hotel lawn"})], "tool_use"),
        resp([block_text("Udaipur fits. Press Apply to bring it closer to budget.")], "end_turn"),
    ])
    body = client.post("/destinations/chat", headers=H, json={"messages": [{"role": "user", "content": "palace feel"}]}).json()
    ev = body["events"]
    assert [c["id"] for c in ev["shortlist"]] == ["udaipur", "jaipur"]
    prop = ev["proposals"][0]
    assert prop["after_total"] < prop["before_total"]

    # Not applied until the couple presses Apply
    assert client.get("/destinations/plan", headers=H).json()["overrides"] == {}
    applied = client.put("/destinations/plan", headers=H, json={"destination": "udaipur", "overrides": prop["overrides"]}).json()
    assert applied["estimate"]["total"] == prop["after_total"]


def test_agent_stops_at_step_limit(monkeypatch):
    loop = [resp([block_tool(f"t{i}", "list_destinations", {})], "tool_use") for i in range(10)]
    use(monkeypatch, loop)
    body = client.post("/destinations/chat", headers=H, json={"messages": [{"role": "user", "content": "x"}]}).json()
    assert "narrow" in body["reply"].lower() and len(body["usage"]["tools"]) == 6


def test_chat_needs_login():
    assert client.post("/stylist/chat", json={"messages": [{"role": "user", "content": "x"}]}).status_code == 401
