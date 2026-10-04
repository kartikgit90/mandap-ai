"""Knowledge base (RAG): chunking, tier rules, editor-only changes, and the agents' search tool."""

import pytest
from fastapi.testclient import TestClient

import app.auth as auth
from app import rag
from app.agents import Events, magazine_search
from app.main import app

client = TestClient(app)
COUPLE = {"Authorization": "Bearer couple-token"}
EDITOR = {"Authorization": "Bearer editor-token"}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    tokens = {"couple-token": {"uid": "c1"}, "editor-token": {"uid": "e1", "role": "editor"}}
    monkeypatch.setattr(auth, "verify_token", lambda t: tokens[t])
    kb = rag.kb_store()
    kb.docs.clear()
    kb.chunks.clear()
    rag.seed()


def test_chunking_keeps_text_and_size():
    text = "\n\n".join(f"Paragraph {i}. " + "Lehenga fittings need time. " * 12 for i in range(6))
    parts = rag.chunk(text)
    assert len(parts) > 2
    assert all(len(p) <= rag.MAX_CHARS * 2 for p in parts)
    assert "Paragraph 5." in " ".join(parts)


def test_couple_search_never_returns_internal_or_confidential():
    # These questions are worded to match the internal and confidential documents.
    for q in ["commission percent for Moti Lane", "Atelier Noor orders email phone contract", "Q3 brand partnership plan"]:
        r = rag.search(q, audience="couple")
        assert all(h["tier"] in {"verified", "published"} for h in r["hits"])
        assert r["blocked"] == []


def test_editor_search_shows_what_was_blocked():
    r = rag.search("commission percent for advertisers", audience="editor")
    assert any(b["tier"] == "internal" for b in r["blocked"])


def test_search_finds_relevant_passage():
    r = rag.search("how early to book a palace in Udaipur", audience="couple")
    assert r["hits"][0]["doc_id"] in {"a-udaipur-guide", "v-booking-windows"}


def test_retiering_hides_a_document_immediately():
    rag.kb_store().set_tier("a-goa-guide", "internal")
    r = rag.search("Goa beach sound restrictions after 10 pm", audience="couple")
    assert all(h["doc_id"] != "a-goa-guide" for h in r["hits"])


def test_agent_tool_cites_sources_and_skips_hidden_tiers():
    ev = Events()
    out = magazine_search(ev, "commission and contact details for Atelier Noor")
    assert all(p["tier"] in {"verified", "published"} for p in out["passages"])
    assert "example-noor" not in str(out)
    assert all(s["tier"] in {"verified", "published"} for s in ev.as_dict()["sources"])


def test_couples_cannot_change_the_knowledge_base():
    body = {"title": "Fake", "tier": "verified", "text": "Something long enough to be a document."}
    assert client.post("/kb/docs", json=body, headers=COUPLE).status_code == 403
    assert client.patch("/kb/docs/a-goa-guide", json={"tier": "internal"}, headers=COUPLE).status_code == 403
    assert client.delete("/kb/docs/a-goa-guide", headers=COUPLE).status_code == 403


def test_couples_see_titles_but_not_text_of_hidden_docs():
    docs = client.get("/kb/docs", headers=COUPLE).json()["docs"]
    hidden = [d for d in docs if d["tier"] in {"internal", "confidential"}]
    assert hidden and all(d["preview"] == "" for d in hidden)
    r = client.post("/kb/search", json={"query": "commission percent"}, headers=COUPLE).json()
    assert all(b["text"] == "" for b in r["blocked"])


def test_editor_adds_uploads_retiers_and_deletes():
    r = client.post("/kb/docs", json={"title": "Mehendi timing", "tier": "published", "issue": "Nov 2026",
                                      "text": "Start the mehendi by 2 pm so the colour sets before the evening."}, headers=EDITOR)
    assert r.status_code == 200 and r.json()["chunks"] == 1
    doc_id = r.json()["id"]
    up = client.post("/kb/upload", headers=EDITOR, data={"title": "Notes", "tier": "internal"},
                     files={"file": ("notes.txt", b"Internal note about the sales targets for next quarter.", "text/plain")})
    assert up.status_code == 200
    bad = client.post("/kb/upload", headers=EDITOR, data={"title": "x", "tier": "internal"},
                      files={"file": ("a.exe", b"binary", "application/octet-stream")})
    assert bad.status_code == 400
    assert client.patch(f"/kb/docs/{doc_id}", json={"tier": "confidential"}, headers=EDITOR).json()["tier"] == "confidential"
    assert client.delete(f"/kb/docs/{doc_id}", headers=EDITOR).status_code == 200
    assert rag.kb_store().get(doc_id) is None


def test_tiny_last_piece_is_folded_into_previous_chunk():
    text = ("Long sentence about bridal fittings and timelines. " * 12) + "\n\nVerified by editors."
    parts = rag.chunk(text)
    assert not any(p == "Verified by editors." for p in parts)
    assert parts[-1].endswith("Verified by editors.")
