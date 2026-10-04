"""The knowledge base and its trust tiers.

Tiers, from most to least trusted:
  verified      editor-approved facts (brand catalogue, destination price bands)
  published     magazine articles
  internal      staff-only notes (e.g. brand commission terms)
  confidential  contracts and contact details

Rule enforced HERE, in code, not by asking the AI nicely:
couples and the AI only ever see `verified` and `published`.
Internal and confidential fields are stripped before anything leaves this module.
"""

from functools import lru_cache
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
COUPLE_TIERS = {"verified", "published"}
HIDDEN_KEYS = {"internal", "contact"}  # internal + confidential sub-records


@lru_cache
def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def _public(record: dict) -> dict:
    """Remove internal and confidential parts of a record."""
    return {k: v for k, v in record.items() if k not in HIDDEN_KEYS and not k.startswith("_")}


# ---------- Brands and products ----------

def brands() -> dict[str, dict]:
    return {b["id"]: _public(b) for b in _load("catalog.json")["brands"] if b["tier"] in COUPLE_TIERS}


def product(pid: str) -> dict | None:
    p = next((p for p in _load("catalog.json")["products"] if p["id"] == pid), None)
    return _with_brand(p) if p else None


def _with_brand(p: dict) -> dict:
    b = brands().get(p["brand_id"])
    out = dict(p, brand=b["name"] if b else "Unknown brand", tier="verified")
    art = article(p.get("article_id")) if p.get("article_id") else None
    if art:
        out["seen_in"] = {"id": art["id"], "title": art["title"], "issue": art["issue"]}
    return out


def search_products(
    *,
    function: str | None = None,
    side: str | None = None,
    kind: str | None = None,
    colors: list[str] | None = None,
    styles: list[str] | None = None,
    max_price: int | None = None,
    limit: int = 12,
) -> list[dict]:
    """Find catalogue items. Colours/styles rank results; function/side/kind/price filter them."""
    colors = [c.lower() for c in (colors or [])]
    styles = [s.lower() for s in (styles or [])]
    out = []
    for p in _load("catalog.json")["products"]:
        if function and function.lower() not in p["functions"]:
            continue
        if side and p["side"] != side.lower():
            continue
        if kind and p["kind"] != kind.lower():
            continue
        if max_price and p["price"] > max_price:
            continue
        score = 2 * len(set(colors) & set(p["colors"])) + len(set(styles) & set(p["style"]))
        out.append((score, p["price"], p))
    out.sort(key=lambda t: (-t[0], t[1]))
    return [_with_brand(p) for _, _, p in out[:limit]]


# ---------- Articles ----------

def article(aid: str | None) -> dict | None:
    for a in _load("articles.json")["articles"]:
        if a["id"] == aid and a["tier"] in COUPLE_TIERS:
            return _public(a)
    return None


def search_articles(query: str, limit: int = 3) -> list[dict]:
    words = {w.strip(".,!?").lower() for w in query.split() if len(w) > 2}
    scored = []
    for a in _load("articles.json")["articles"]:
        if a["tier"] not in COUPLE_TIERS:
            continue
        text = " ".join([a["title"], a["summary"], " ".join(a["tags"])]).lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, a))
    scored.sort(key=lambda t: -t[0])
    return [_public(a) for _, a in scored[:limit]]


# ---------- Destinations ----------

LINE_LABELS = {
    "venue_rooms": "Venue + rooms",
    "food": "Food + bar",
    "decor": "Decor",
    "travel": "Guest travel",
    "photo_ent": "Photo + entertainment",
    "misc": "Planner + misc",
}


def destinations() -> list[dict]:
    d = _load("destinations.json")
    return [dict(_public(x), valid_until=d["valid_until"]) for x in d["destinations"] if x["tier"] in COUPLE_TIERS]


def destination(did: str) -> dict | None:
    return next((d for d in destinations() if d["id"] == did), None)


def estimate(did: str, guests: int, days: int, overrides: dict[str, int] | None = None) -> dict | None:
    """Budget estimate from verified price bands. Pure maths, no AI, so it is always consistent.

    overrides: replace a line's midpoint with a fixed amount, e.g. {"decor": 600000}.
    """
    d = destination(did)
    if not d:
        return None
    b = d["bands"]
    nights = max(days - 1, 1)
    mid = lambda lo_hi: (lo_hi[0] + lo_hi[1]) / 2  # noqa: E731

    ranges = {
        "venue_rooms": [x * guests * nights for x in b["room_per_guest_night"]],
        "food": [x * guests * days for x in b["food_per_guest_day"]],
        "decor": list(b["decor"]),
        "travel": [x * guests for x in b["travel_per_guest"]],
        "photo_ent": list(b["photo_ent"]),
    }
    lines = {k: mid(v) for k, v in ranges.items()}
    for k, v in (overrides or {}).items():
        if k in lines:
            lines[k] = float(v)
    subtotal = sum(lines.values())
    lines["misc"] = subtotal * b["misc_pct"]
    low = sum(v[0] for v in ranges.values()) * (1 + b["misc_pct"])
    high = sum(v[1] for v in ranges.values()) * (1 + b["misc_pct"])

    return {
        "destination": d["id"],
        "name": d["name"],
        "guests": guests,
        "days": days,
        "lines": [{"key": k, "label": LINE_LABELS[k], "amount": round(v, -3)} for k, v in lines.items()],
        "total": round(sum(lines.values()), -3),
        "range": [round(low, -4), round(high, -4)],
        "overrides": overrides or {},
        "source": {"tier": "verified", "title": "Destination price bands", "valid_until": d["valid_until"]},
    }
