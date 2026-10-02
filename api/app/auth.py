"""Login check for every protected API call.

How it works:
1. The web app signs the user in with Firebase Auth and gets an ID token.
2. It sends that token in the header:  Authorization: Bearer <token>
3. We verify the token with Firebase and read the user's role from it.

Roles live in Firebase "custom claims", so a couple can never make themselves an admin.
Anyone without a role set is treated as a couple.
"""

from dataclasses import dataclass
from typing import Literal

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth

from app.config import get_settings

Role = Literal["couple", "editor", "admin"]
ROLE_RANK: dict[str, int] = {"couple": 1, "editor": 2, "admin": 3}

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    email: str | None
    role: Role


def _firebase_app() -> firebase_admin.App:
    """Start Firebase once. On Cloud Run it uses the service's own Google identity,
    so no key file is needed."""
    try:
        return firebase_admin.get_app()
    except ValueError:
        return firebase_admin.initialize_app(options={"projectId": get_settings().gcp_project_id})


def verify_token(token: str) -> dict:
    _firebase_app()
    return fb_auth.verify_id_token(token)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing login token")
    try:
        claims = verify_token(creds.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired login token")

    role = claims.get("role", "couple")
    if role not in ROLE_RANK:
        role = "couple"
    return CurrentUser(uid=claims["uid"], email=claims.get("email"), role=role)


def require_role(minimum: Role):
    """Use on a route to allow only editors, or only admins, e.g.
    Depends(require_role("editor"))."""

    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have access to this")
        return user

    return checker
