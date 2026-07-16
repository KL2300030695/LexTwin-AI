"""Firebase Authentication: verifies the ID token every protected request
must carry, and enforces role-based authorization on top of it.

Firebase Auth answers "who is this" (verify_id_token); it does NOT have a
concept of roles by itself. Roles (reviewer/approver/admin) are stored as
Firebase custom claims -- baked into the ID token itself by
firebase_admin.auth.set_custom_user_claims(), so authorizing a request never
needs an extra Firestore read, just a decode of the token already being
verified.

This module doesn't touch app.firebase's Firestore client, but does reuse
its Firebase Admin SDK app initialization (both live under the same
firebase_admin.initialize_app() call) -- see ensure_admin_app below.
"""
from __future__ import annotations

from enum import Enum

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


class Role(str, Enum):
    REVIEWER = "reviewer"
    APPROVER = "approver"
    ADMIN = "admin"


# Roles are cumulative: an approver can do everything a reviewer can, an
# admin can do everything an approver can. _ROLE_RANK expresses that so
# require_role(Role.APPROVER) also accepts an admin token.
_ROLE_RANK = {Role.REVIEWER: 0, Role.APPROVER: 1, Role.ADMIN: 2}


class CurrentUser(BaseModel):
    uid: str
    email: str | None = None
    role: Role = Role.REVIEWER


def ensure_admin_app() -> None:
    """Firebase Admin SDK apps are a single global registry keyed by name --
    initializing it twice raises. app.firebase._init_firebase() already does
    this exact init for Firestore; if that's already run (USE_FIREBASE=true),
    reuse it. Otherwise (USE_FIREBASE=false, local-disk storage mode) init it
    here just for Auth, since Auth doesn't depend on Firestore being enabled.
    """
    import firebase_admin

    if firebase_admin._apps:  # already initialized, by us or by app.firebase
        return
    from pathlib import Path

    from firebase_admin import credentials

    cred_path = Path(settings.FIREBASE_CREDENTIALS_PATH)
    if not cred_path.exists():
        raise RuntimeError(
            f"Firebase Authentication requires a service account key, but none was found at {cred_path}. "
            "Download one from the Firebase console (Project Settings -> Service Accounts) and set "
            "FIREBASE_CREDENTIALS_PATH."
        )
    firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency: verifies the bearer token's Firebase ID token and
    returns the caller's identity + role. Raises 401 if missing/invalid.

    Every protected router depends on this (directly, or via require_role
    below) -- there is no endpoint that silently allows an unauthenticated
    caller through."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token.")

    ensure_admin_app()
    from firebase_admin import auth as firebase_auth

    try:
        decoded = firebase_auth.verify_id_token(credentials.credentials)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}") from e

    raw_role = decoded.get("role", Role.REVIEWER.value)
    try:
        role = Role(raw_role)
    except ValueError:
        role = Role.REVIEWER  # an unrecognized claim value degrades to the least-privileged role, not a crash

    return CurrentUser(uid=decoded["uid"], email=decoded.get("email"), role=role)


def require_role(minimum: Role):
    """Returns a FastAPI dependency that accepts `minimum` role or anything
    ranked above it (see _ROLE_RANK) -- e.g. require_role(Role.APPROVER)
    lets both approvers and admins through, rejects reviewers with 403."""

    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if _ROLE_RANK[user.role] < _ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires the '{minimum.value}' role or higher; you have '{user.role.value}'.",
            )
        return user

    return _dependency
