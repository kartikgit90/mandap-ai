"""The magazine's knowledge base, searched by meaning (RAG).

How it works:
  1. An editor adds a document (an article, a fact sheet, a sales note) and picks its trust tier.
  2. We split it into short passages ("chunks") of a few sentences each.
  3. Google's embedding model turns each chunk into 768 numbers that capture its meaning.
  4. Chunks + numbers are stored in Firestore, which can find the chunks closest in meaning to a question.
  5. The AI agents call search() and answer from the passages it returns, citing each source.

The tier rule is enforced HERE, in code: a couple-facing search only ever returns
`verified` and `published` chunks. Firestore filters on it, and we check again afterwards.
Internal and confidential documents are stored, but the AI never receives them.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.config import get_settings
from app.store import new_id, now

log = logging.getLogger("mandap")

TIERS = ["verified", "published", "internal", "confidential"]
COUPLE_TIERS = {"verified", "published"}
Audience = Literal["couple", "editor"]

MAX_CHARS = 500  # target chunk size; a few sentences, enough to answer from
SEED = Path(__file__).parent / "data" / "kb_seed.json"


# ---------- 1. Splitting into chunks ----------

def chunk(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """Split on paragraphs, pack them up to max_chars, and split long paragraphs by sentence.
    Each chunk repeats the last sentence of the previous one, so an idea cut in half is not lost."""
    text = re.sub(r"\r\n?", "\n", text).strip()
    if not text:
        return []
    sentences: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = " ".join(para.split())
        if para:
            sentences += re.split(r"(?<=[.!?])\s+", para)
            sentences.append("\n")  # paragraph break marker
    chunks, cur = [], ""
    for s in sentences:
        if s == "\n":
            if len(cur) >= max_chars * 0.6:
                chunks.append(cur.strip())
                cur = ""
            continue
        if cur and len(cur) + len(s) + 1 > max_chars:
            chunks.append(cur.strip())
            last = re.split(r"(?<=[.!?])\s+", cur.strip())[-1]
            cur = (last + " " if len(last) < max_chars // 3 else "")
        cur += s + " "
    if cur.strip():
        chunks.append(cur.strip())
    return [c[: max_chars * 2] for c in chunks]


# ---------- 2. Turning text into numbers (embeddings) ----------

class VertexEmbedder:
    """Google's embedding model on Vertex AI. Costs fractions of a paisa per document."""

    def __init__(self):
        from google import genai

        s = get_settings()
        self.model, self.dim = s.embed_model, s.embed_dim
        self.clients = [genai.Client(vertexai=True, project=s.gcp_project_id, location=r)
                        for r in s.embed_regions.split(",")]

    def embed(self, texts: list[str], kind: Literal["document", "query"]) -> list[list[float]]:
        from google.genai import types

        cfg = types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT" if kind == "document" else "RETRIEVAL_QUERY",
            output_dimensionality=self.dim,
        )
        last_err = None
        for client in self.clients:  # Mumbai first; fall back to another region if the model isn't there
            try:
                out = []
                for t in texts:  # one at a time: the model accepts one text per request
                    r = client.models.embed_content(model=self.model, contents=t, config=cfg)
                    out.append(_normalise(list(r.embeddings[0].values)))
                return out
            except Exception as e:  # noqa: BLE001
                last_err = e
                log.warning("embedding failed in one region, trying next: %s", e)
        raise RuntimeError(f"Embedding failed: {last_err}")


class HashEmbedder:
    """Offline stand-in for tests and local runs: word overlap, no network, no cost."""

    dim = 256

    def embed(self, texts: list[str], kind: str = "document") -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.dim
            for w in re.findall(r"[a-z]{3,}", t.lower()):
                v[int(hashlib.md5(w.rstrip("s").encode()).hexdigest(), 16) % self.dim] += 1.0
            out.append(_normalise(v))
        return out


def _normalise(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


@lru_cache
def embedder():
    return VertexEmbedder() if get_settings().embed_backend == "vertex" else HashEmbedder()


# ---------- 3. Where chunks live ----------

class MemoryKB:
    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.chunks: dict[str, dict] = {}

    def save(self, doc: dict, chunks: list[dict]):
        self.delete(doc["id"])
        self.docs[doc["id"]] = doc
        for c in chunks:
            self.chunks[c["id"]] = c

    def get(self, doc_id):
        return self.docs.get(doc_id)

    def list(self):
        return sorted(self.docs.values(), key=lambda d: d.get("created_at", ""), reverse=True)

    def set_tier(self, doc_id, tier):
        self.docs[doc_id].update(tier=tier, public=tier in COUPLE_TIERS)
        for c in self.chunks.values():
            if c["doc_id"] == doc_id:
                c.update(tier=tier, public=tier in COUPLE_TIERS)

    def delete(self, doc_id):
        self.docs.pop(doc_id, None)
        for cid in [k for k, c in self.chunks.items() if c["doc_id"] == doc_id]:
            del self.chunks[cid]

    def nearest(self, qv: list[float], public: bool, k: int) -> list[dict]:
        rows = [c for c in self.chunks.values() if c["public"] == public]
        scored = [(sum(a * b for a, b in zip(qv, c["embedding"])), c) for c in rows]
        scored.sort(key=lambda t: -t[0])
        return [dict(c, score=round(s, 3)) for s, c in scored[:k] if s > 0]


class FirestoreKB:
    """kb_docs/{id} holds the document; kb_chunks/{id} holds each passage and its embedding.
    Needs one Firestore vector index on kb_chunks: (public, embedding)."""

    def __init__(self):
        from app.store import store  # make sure firebase_admin is initialised

        self.db = store().db
        from google.cloud.firestore_v1.vector import Vector

        self.Vector = Vector

    def save(self, doc, chunks):
        self.delete(doc["id"])
        batch, n = self.db.batch(), 0
        batch.set(self.db.collection("kb_docs").document(doc["id"]), doc)
        for c in chunks:
            data = dict(c, embedding=self.Vector(c["embedding"]))
            batch.set(self.db.collection("kb_chunks").document(c["id"]), data)
            n += 1
            if n % 400 == 0:
                batch.commit()
                batch = self.db.batch()
        batch.commit()

    def get(self, doc_id):
        s = self.db.collection("kb_docs").document(doc_id).get()
        return s.to_dict() if s.exists else None

    def list(self):
        rows = [s.to_dict() for s in self.db.collection("kb_docs").stream()]
        return sorted(rows, key=lambda d: d.get("created_at", ""), reverse=True)

    def _chunk_refs(self, doc_id):
        from google.cloud.firestore_v1.base_query import FieldFilter

        return [s.reference for s in self.db.collection("kb_chunks").where(filter=FieldFilter("doc_id", "==", doc_id)).stream()]

    def set_tier(self, doc_id, tier):
        upd = {"tier": tier, "public": tier in COUPLE_TIERS}
        batch = self.db.batch()
        batch.update(self.db.collection("kb_docs").document(doc_id), upd)
        for ref in self._chunk_refs(doc_id):
            batch.update(ref, upd)
        batch.commit()

    def delete(self, doc_id):
        batch = self.db.batch()
        for ref in self._chunk_refs(doc_id):
            batch.delete(ref)
        batch.delete(self.db.collection("kb_docs").document(doc_id))
        batch.commit()

    def nearest(self, qv, public, k):
        from google.cloud.firestore_v1.base_query import FieldFilter
        from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

        q = (self.db.collection("kb_chunks")
             .where(filter=FieldFilter("public", "==", public))
             .find_nearest(vector_field="embedding", query_vector=self.Vector(qv),
                           distance_measure=DistanceMeasure.COSINE, limit=k, distance_result_field="distance"))
        out = []
        for s in q.stream():
            d = s.to_dict()
            d.pop("embedding", None)
            d["score"] = round(1 - d.pop("distance", 1.0), 3)  # cosine distance -> similarity
            out.append(d)
        return out


@lru_cache
def kb_store():
    return FirestoreKB() if get_settings().store_backend == "firestore" else MemoryKB()


# ---------- 4. What the app calls ----------

def ingest(*, title: str, text: str, tier: str, issue: str = "", doc_id: str | None = None,
           source: str = "pasted", added_by: str = "") -> dict:
    if tier not in TIERS:
        raise ValueError(f"tier must be one of {TIERS}")
    parts = chunk(text)
    if not parts:
        raise ValueError("Document has no text")
    doc_id = doc_id or new_id()
    # The title is embedded with each chunk so a passage keeps its context.
    vectors = embedder().embed([f"{title}\n{p}" for p in parts], "document")
    doc = {"id": doc_id, "title": title, "issue": issue, "tier": tier, "public": tier in COUPLE_TIERS,
           "source": source, "chunks": len(parts), "chars": len(text), "preview": text[:280],
           "added_by": added_by, "created_at": now()}
    chunks = [{"id": f"{doc_id}-{i:03d}", "doc_id": doc_id, "i": i, "title": title, "issue": issue,
               "tier": tier, "public": tier in COUPLE_TIERS, "text": p, "embedding": v}
              for i, (p, v) in enumerate(zip(parts, vectors))]
    kb_store().save(doc, chunks)
    log.info("kb ingest doc=%s tier=%s chunks=%s", doc_id, tier, len(chunks))
    return doc


def search(query: str, *, audience: Audience = "couple", k: int = 4) -> dict:
    """Passages closest in meaning to the query.
    audience='couple' (the AI agents, couples): verified + published only.
    audience='editor' (knowledge-base console): also returns what was blocked, to show the tiers working."""
    qv = embedder().embed([query], "query")[0]
    allowed = kb_store().nearest(qv, public=True, k=k)
    allowed = [h for h in allowed if h.get("tier") in COUPLE_TIERS]  # belt and braces
    blocked = kb_store().nearest(qv, public=False, k=k) if audience == "editor" else []
    return {"hits": allowed, "blocked": blocked}


def seed() -> int:
    """Load the demo documents (articles, fact sheets, plus internal/confidential notes to prove they stay hidden)."""
    docs = json.loads(SEED.read_text())["docs"]
    for d in docs:
        ingest(title=d["title"], text=d["text"], tier=d["tier"], issue=d.get("issue", ""),
               doc_id=d["id"], source="demo seed", added_by="seed")
    return len(docs)


def extract_text(filename: str, data: bytes) -> str:
    """Text from an uploaded .txt, .md or .pdf file."""
    name = filename.lower()
    if name.endswith(".pdf"):
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages[:60])
    if name.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    raise ValueError("Upload a .txt, .md or .pdf file")
