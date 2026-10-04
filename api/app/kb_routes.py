"""Knowledge base console API.

Editors and admins add, re-tier and delete documents. Everyone logged in can browse the list
and try a search, but only editors see the text of internal and confidential material.
"""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app import rag
from app.auth import ROLE_RANK, CurrentUser, get_current_user, require_role

router = APIRouter(prefix="/kb")
Tier = Literal["verified", "published", "internal", "confidential"]
MAX_UPLOAD = 5 * 1024 * 1024


def _is_editor(user: CurrentUser) -> bool:
    return ROLE_RANK[user.role] >= ROLE_RANK["editor"]


def _view(doc: dict, editor: bool) -> dict:
    d = {k: v for k, v in doc.items() if k != "added_by"}
    if not editor and doc.get("tier") not in rag.COUPLE_TIERS:
        d["preview"] = ""  # couples see that it exists and its tier, not what it says
    return d


@router.get("/docs")
def list_docs(user: CurrentUser = Depends(get_current_user)):
    editor = _is_editor(user)
    return {"can_edit": editor, "docs": [_view(d, editor) for d in rag.kb_store().list()]}


class DocIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    issue: str = Field(default="", max_length=60)
    tier: Tier
    text: str = Field(min_length=20, max_length=200_000)


def _ingest(**kw):
    try:
        return rag.ingest(**kw)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # embedding service down, index missing, etc.
        raise HTTPException(502, f"Couldn't add to the knowledge base: {e}")


@router.post("/docs")
def add_doc(body: DocIn, user: CurrentUser = Depends(require_role("editor"))):
    return _ingest(title=body.title, text=body.text, tier=body.tier, issue=body.issue,
                   source="pasted", added_by=user.uid)


@router.post("/upload")
async def upload(file: UploadFile = File(...), title: str = Form(...), tier: Tier = Form(...),
                 issue: str = Form(""), user: CurrentUser = Depends(require_role("editor"))):
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(400, "File is larger than 5 MB")
    try:
        text = rag.extract_text(file.filename or "", data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if len(text.strip()) < 20:
        raise HTTPException(400, "Couldn't find text in that file (scanned PDFs aren't supported yet)")
    return _ingest(title=title[:160], text=text[:200_000], tier=tier, issue=issue[:60],
                   source=file.filename or "upload", added_by=user.uid)


class TierIn(BaseModel):
    tier: Tier


@router.patch("/docs/{doc_id}")
def change_tier(doc_id: str, body: TierIn, user: CurrentUser = Depends(require_role("editor"))):
    if not rag.kb_store().get(doc_id):
        raise HTTPException(404, "Document not found")
    rag.kb_store().set_tier(doc_id, body.tier)
    return rag.kb_store().get(doc_id)


@router.delete("/docs/{doc_id}")
def delete_doc(doc_id: str, user: CurrentUser = Depends(require_role("editor"))):
    rag.kb_store().delete(doc_id)
    return {"ok": True}


@router.post("/seed")
def seed(user: CurrentUser = Depends(require_role("editor"))):
    try:
        return {"added": rag.seed()}
    except Exception as e:
        raise HTTPException(502, f"Couldn't load demo documents: {e}")


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=300)


@router.post("/search")
def search(body: SearchIn, user: CurrentUser = Depends(get_current_user)):
    """Shows exactly what the AI would receive for this question, and what the tier rule held back."""
    editor = _is_editor(user)
    try:
        r = rag.search(body.query, audience="editor", k=4)
    except Exception as e:
        raise HTTPException(502, f"Search failed: {e}")
    hits = [{k: v for k, v in h.items() if k != "embedding"} for h in r["hits"]]
    blocked = [{"doc_id": b["doc_id"], "title": b["title"], "tier": b["tier"], "score": b["score"],
                "text": b["text"] if editor else ""} for b in r["blocked"]]
    return {"hits": hits, "blocked": blocked}
