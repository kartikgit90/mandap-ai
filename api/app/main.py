"""Entry point for the Mandap AI backend."""

import logging
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware

from app import llm
from app.auth import CurrentUser, get_current_user, require_role
from app.config import get_settings
from app.routes import router

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("mandap")

app = FastAPI(title="Mandap AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.middleware("http")
async def trace_id(request: Request, call_next):
    """Give every request an id, so one couple's request can be followed
    across logs, agents and tool calls."""
    tid = request.headers.get("x-trace-id") or uuid.uuid4().hex[:16]
    request.state.trace_id = tid
    response = await call_next(request)
    response.headers["x-trace-id"] = tid
    log.info("trace=%s %s %s -> %s", tid, request.method, request.url.path, response.status_code)
    return response


@app.get("/health")
def health():
    """Cloud Run calls this to check the service is alive. No login needed."""
    return {"status": "ok", "env": settings.env, "llm_provider": settings.llm_provider}


@app.get("/me")
def me(user: CurrentUser = Depends(get_current_user)):
    """Who am I? Any logged-in user."""
    return {"uid": user.uid, "email": user.email, "role": user.role}


@app.get("/admin/ping")
def admin_ping(user: CurrentUser = Depends(require_role("admin"))):
    """Admins only. Used to test that role checks work."""
    return {"ok": True, "uid": user.uid}


@app.post("/admin/llm-test")
def admin_llm_test(user: CurrentUser = Depends(require_role("admin"))):
    """Admins only. Sends one tiny question to Claude to check the connection works."""
    try:
        r = llm.ask(
            "In one short sentence, give one practical tip for planning a mehendi function.",
            system="You are a helpful Indian wedding planning assistant. Be brief.",
            tier="fast",
            max_tokens=100,
        )
    except Exception as e:  # show the real reason to the admin, it helps debugging
        log.exception("LLM test failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Claude call failed: {e}")
    log.info("llm_test model=%s in=%s out=%s cost_inr=%s ms=%s",
             r.model, r.tokens_in, r.tokens_out, r.cost_inr, r.latency_ms)
    return {
        "reply": r.text,
        "model": r.model,
        "provider": settings.llm_provider,
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "cost_inr": r.cost_inr,
        "latency_ms": r.latency_ms,
    }
