"""The tier rules are the most important safety property: test them directly."""

import json

from app import knowledge as kb


def test_no_internal_or_confidential_in_brands():
    dumped = json.dumps(kb.brands())
    assert "commission" not in dumped
    assert "email" not in dumped and "phone" not in dumped


def test_products_never_carry_hidden_brand_data():
    for p in kb.search_products(limit=100):
        dumped = json.dumps(p)
        assert "commission" not in dumped
        assert "@" not in dumped  # no email addresses


def test_search_filters_and_ranks():
    res = kb.search_products(function="sangeet", side="bride", kind="outfit", colors=["emerald"], max_price=200000)
    assert res, "expected sangeet outfits"
    assert all("sangeet" in p["functions"] and p["price"] <= 200000 for p in res)
    assert res[0]["id"] == "p01"  # emerald ranks first
    assert res[0]["seen_in"]["issue"] == "Oct 2026"


def test_articles_search():
    res = kb.search_articles("udaipur palace wedding")
    assert res and res[0]["id"] == "a-udaipur-guide"


def test_estimate_is_consistent_and_overridable():
    e = kb.estimate("udaipur", guests=220, days=3)
    assert e["range"][0] <= e["total"] <= e["range"][1]
    assert sum(l["amount"] for l in e["lines"]) == e["total"] or abs(sum(l["amount"] for l in e["lines"]) - e["total"]) < 5000
    cheaper = kb.estimate("udaipur", guests=220, days=3, overrides={"decor": 500000})
    assert cheaper["total"] < e["total"]


def test_unknown_destination():
    assert kb.estimate("atlantis", 100, 2) is None
