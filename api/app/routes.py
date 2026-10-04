"""API for the couple's app: wedding details, Shop the Look, Destination weddings."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import knowledge as kb
from app import llm
from app.agents import Events, destination as dest_agent, stylist as stylist_agent
from app.auth import CurrentUser, get_current_user
from app.store import new_id, now, store, wedding

log = logging.getLogger("mandap")
router = APIRouter()


# ---------- Wedding details ----------

class Wedding(BaseModel):
    couple: str = Field(max_length=80)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    guests: int = Field(ge=10, le=3000)
    days: int = Field(ge=1, le=7)
    budget: int = Field(ge=100000, le=500000000)
    functions: list[str] = Field(max_length=10)


@router.get("/wedding")
def get_wedding(user: CurrentUser = Depends(get_current_user)):
    return wedding(user.uid)


@router.put("/wedding")
def put_wedding(body: Wedding, user: CurrentUser = Depends(get_current_user)):
    return store().put(user.uid, "profile", "wedding", body.model_dump())


# ---------- Shared chat plumbing ----------

class Msg(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatIn(BaseModel):
    messages: list[Msg] = Field(min_length=1, max_length=30)
    context: dict = Field(default_factory=dict)


def _run(system, tools, handlers, body: ChatIn, ev: Events, agent: str, uid: str):
    if body.messages[-1].role != "user":
        raise HTTPException(400, "Last message must be from the user")
    history = [m.model_dump() for m in body.messages[-12:]]
    while history and history[0]["role"] != "user":  # Claude needs the first turn to be the user's
        history.pop(0)
    try:
        r = llm.run_agent(system=system, messages=history, tools=tools, handlers=handlers)
    except Exception as e:
        log.exception("agent %s failed", agent)
        raise HTTPException(502, f"The AI couldn't answer right now ({type(e).__name__}). Please try again.")
    log.info("agent=%s uid=%s tools=%s in=%s out=%s cost_inr=%s stop=%s",
             agent, uid[:6], [c[0] for c in r.tool_calls], r.tokens_in, r.tokens_out, r.cost_inr, r.stopped_early)
    return {
        "reply": r.text,
        "events": ev.as_dict(),
        "usage": {"model": r.model, "tokens_in": r.tokens_in, "tokens_out": r.tokens_out,
                  "cost_inr": r.cost_inr, "tools": [c[0] for c in r.tool_calls]},
    }


# ---------- Shop the Look ----------

@router.post("/stylist/chat")
def stylist_chat(body: ChatIn, user: CurrentUser = Depends(get_current_user)):
    ev = Events()
    system, tools, handlers = stylist_agent.build(user.uid, body.context, ev)
    return _run(system, tools, handlers, body, ev, "stylist", user.uid)


class SaveLook(BaseModel):
    look: dict


@router.get("/looks")
def list_looks(user: CurrentUser = Depends(get_current_user)):
    return store().list(user.uid, "looks")


@router.post("/looks")
def save_look(body: SaveLook, user: CurrentUser = Depends(get_current_user)):
    # Re-price from the catalogue so a client can never save made-up prices.
    pieces = [kb.product(p["id"]) for p in body.look.get("pieces", [])]
    if not pieces or any(p is None for p in pieces):
        raise HTTPException(400, "Look has unknown pieces")
    look = {k: body.look.get(k) for k in ("title", "function", "side", "why")}
    look["pieces"] = [{"id": p["id"], "name": p["name"], "brand": p["brand"], "kind": p["kind"], "price": p["price"],
                       "colors": p["colors"], "seen_in": p.get("seen_in")} for p in pieces]
    look["total"] = sum(p["price"] for p in pieces)
    look["created_at"] = now()
    return store().put(user.uid, "looks", new_id(), look)


@router.delete("/looks/{look_id}")
def delete_look(look_id: str, user: CurrentUser = Depends(get_current_user)):
    store().delete(user.uid, "looks", look_id)
    return {"ok": True}


@router.get("/enquiries")
def list_enquiries(user: CurrentUser = Depends(get_current_user)):
    return store().list(user.uid, "enquiries")


@router.post("/enquiries/{enquiry_id}/send")
def send_enquiry(enquiry_id: str, user: CurrentUser = Depends(get_current_user)):
    """The couple's approval. Only here does a draft become 'sent'.
    In the demo, 'sent' means delivered to the brand's inbox in the admin console; no real email goes out."""
    e = store().get(user.uid, "enquiries", enquiry_id)
    if not e:
        raise HTTPException(404, "Enquiry not found")
    if e["status"] != "draft":
        return e
    e.update(status="sent", sent_at=now())
    e.pop("id", None)
    return store().put(user.uid, "enquiries", enquiry_id, e)


@router.delete("/enquiries/{enquiry_id}")
def discard_enquiry(enquiry_id: str, user: CurrentUser = Depends(get_current_user)):
    e = store().get(user.uid, "enquiries", enquiry_id)
    if e and e["status"] == "draft":
        store().delete(user.uid, "enquiries", enquiry_id)
    return {"ok": True}


# ---------- Destination weddings ----------

@router.get("/destinations")
def list_destinations(user: CurrentUser = Depends(get_current_user)):
    w = wedding(user.uid)
    return [dest_agent.card(d, w) for d in kb.destinations()]


@router.get("/destinations/plan")
def get_plan(user: CurrentUser = Depends(get_current_user)):
    w = wedding(user.uid)
    plan = store().get(user.uid, "plans", "destination") or {}
    chosen = plan.get("destination") or (plan.get("shortlist") or ["udaipur"])[0]
    shortlist_ids = plan.get("shortlist") or ["udaipur", "jaipur", "goa"]
    return {
        "wedding": w,
        "destination": chosen,
        "overrides": plan.get("overrides") or {},
        "shortlist": [dest_agent.card(d, w) for d in kb.destinations() if d["id"] in shortlist_ids],
        "estimate": kb.estimate(chosen, w["guests"], w["days"], plan.get("overrides") if plan.get("destination") == chosen else None),
    }


class PlanIn(BaseModel):
    destination: str
    overrides: dict[str, int] = Field(default_factory=dict)


@router.put("/destinations/plan")
def put_plan(body: PlanIn, user: CurrentUser = Depends(get_current_user)):
    if not kb.destination(body.destination):
        raise HTTPException(400, "Unknown destination")
    allowed = {"venue_rooms", "food", "decor", "travel", "photo_ent"}
    overrides = {k: v for k, v in body.overrides.items() if k in allowed and 0 <= v <= 100_000_000}
    old = store().get(user.uid, "plans", "destination") or {}
    old.pop("id", None)
    store().put(user.uid, "plans", "destination", dict(old, destination=body.destination, overrides=overrides, updated_at=now()))
    return get_plan(user)


@router.post("/destinations/chat")
def destination_chat(body: ChatIn, user: CurrentUser = Depends(get_current_user)):
    ev = Events()
    system, tools, handlers = dest_agent.build(user.uid, ev)
    return _run(system, tools, handlers, body, ev, "destination", user.uid)
