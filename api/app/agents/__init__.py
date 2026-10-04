"""AI agents. Each agent = a system prompt + a small set of tools it may call.

Agents never send messages or change saved plans by themselves. Anything with an effect
outside the chat (contacting a brand, changing the plan) is created as a *proposal* that
the couple must approve with a button in the app.
"""


def lakh(amount: float) -> str:
    """₹ in Indian style: 4500000 -> '₹45 L', 55000 -> '₹55K'."""
    if amount >= 100000:
        v = amount / 100000
        return f"₹{v:.1f} L".replace(".0 L", " L")
    return f"₹{round(amount / 1000)}K"


class Events:
    """Structured things the agent produced this turn, for the app to show as cards."""

    def __init__(self):
        self.looks: list[dict] = []
        self.drafts: list[dict] = []
        self.proposals: list[dict] = []
        self.shortlist: list[dict] = []
        self.estimates: list[dict] = []
        self._sources: dict[str, dict] = {}

    def source(self, key: str, tier: str, title: str):
        self._sources[key] = {"tier": tier, "title": title}

    def as_dict(self) -> dict:
        return {
            "looks": self.looks,
            "drafts": self.drafts,
            "proposals": self.proposals,
            "shortlist": self.shortlist,
            "estimates": self.estimates,
            "sources": list(self._sources.values()),
        }


def magazine_search(ev: "Events", query: str) -> dict:
    """RAG search over the magazine's knowledge base, for the agents' search_magazine tool.
    Only verified and published passages can come back (enforced in rag.search).
    If the knowledge base is empty or unreachable, falls back to keyword search over article summaries."""
    import logging

    from app import knowledge as kb
    from app import rag

    try:
        hits = rag.search(query, audience="couple", k=4)["hits"]
    except Exception:  # noqa: BLE001
        logging.getLogger("mandap").exception("RAG search failed, using keyword fallback")
        hits = []
    if hits:
        for h in hits:
            ev.source(h["doc_id"], h["tier"], f'{h["issue"]} · {h["title"]}' if h.get("issue") else h["title"])
        return {"passages": [{"source": h["title"], "issue": h.get("issue", ""), "tier": h["tier"], "text": h["text"]} for h in hits],
                "note": "Answer from these passages. Mention the source by title when you use one."}
    arts = kb.search_articles(query)
    for x in arts:
        ev.source(x["id"], "published", f'{x["issue"]} · {x["title"]}')
    return {"passages": [{"source": x["title"], "issue": x["issue"], "tier": "published", "text": x["summary"]} for x in arts]}
