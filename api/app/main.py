"""Entry point for the Mandap AI backend."""

import logging
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.auth import CurrentUser, get_current_user, require_role
from app.config import get_settings

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
