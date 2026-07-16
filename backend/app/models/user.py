"""User/role models for the auth API (app/routers/auth.py). Firebase Auth
itself owns identity (email, password, uid); these models only describe the
role-related view this app layers on top via custom claims."""
from __future__ import annotations

from pydantic import BaseModel

from app.auth import Role


class UserProfile(BaseModel):
    uid: str
    email: str | None = None
    role: Role


class RoleUpdate(BaseModel):
    role: Role
