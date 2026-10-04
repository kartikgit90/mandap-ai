"""Where each couple's data lives: wedding details, saved looks, enquiries, destination plan.

Firestore in the cloud; an in-memory store for tests and local runs.
Every record sits under users/{uid}/..., so one couple can never read another's data.
"""

from datetime import datetime, timezone
from functools import lru_cache
import uuid

from app.config import get_settings

DEFAULT_WEDDING = {
    "couple": "Ananya & Rohan",
    "date": "2027-02-12",
    "guests": 220,
    "days": 3,
    "budget": 4500000,
    "functions": ["haldi", "mehendi", "sangeet", "pheras", "reception"],
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self):
        self.docs: dict[tuple, dict] = {}

    def get(self, uid, coll, doc_id):
        return self.docs.get((uid, coll, doc_id))

    def put(self, uid, coll, doc_id, data):
        self.docs[(uid, coll, doc_id)] = dict(data, id=doc_id)
        return self.docs[(uid, coll, doc_id)]

    def list(self, uid, coll):
        rows = [v for (u, c, _), v in self.docs.items() if u == uid and c == coll]
        return sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)

    def delete(self, uid, coll, doc_id):
        self.docs.pop((uid, coll, doc_id), None)


class FirestoreStore:
    def __init__(self):
        import firebase_admin
        from firebase_admin import firestore

        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(options={"projectId": get_settings().gcp_project_id})
        self.db = firestore.client()

    def _c(self, uid, coll):
        return self.db.collection("users").document(uid).collection(coll)

    def get(self, uid, coll, doc_id):
        snap = self._c(uid, coll).document(doc_id).get()
        return dict(snap.to_dict(), id=snap.id) if snap.exists else None

    def put(self, uid, coll, doc_id, data):
        self._c(uid, coll).document(doc_id).set(data)
        return dict(data, id=doc_id)

    def list(self, uid, coll):
        rows = [dict(s.to_dict(), id=s.id) for s in self._c(uid, coll).stream()]
        return sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)

    def delete(self, uid, coll, doc_id):
        self._c(uid, coll).document(doc_id).delete()


@lru_cache
def store():
    return FirestoreStore() if get_settings().store_backend == "firestore" else MemoryStore()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def wedding(uid: str) -> dict:
    return store().get(uid, "profile", "wedding") or dict(DEFAULT_WEDDING, id="wedding")
