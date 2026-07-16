from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth import CurrentUser, Role, get_current_user, require_role
from app.models.user import RoleUpdate, UserProfile
from app.services import user_service

router = APIRouter()


@router.get("/me", response_model=UserProfile)
def me(user: CurrentUser = Depends(get_current_user)):
    return UserProfile(uid=user.uid, email=user.email, role=user.role)


@router.post("/bootstrap-admin", response_model=UserProfile)
def bootstrap_admin(user: CurrentUser = Depends(get_current_user)):
    """One-time escape hatch: promotes the calling (already-authenticated)
    user to admin, but only while zero admins exist yet. Every call after
    the first admin is assigned 403s -- see user_service.bootstrap_first_admin.
    """
    try:
        return user_service.bootstrap_first_admin(user)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/users", response_model=list[UserProfile])
def list_users(_: CurrentUser = Depends(require_role(Role.ADMIN))):
    return user_service.list_users()


@router.put("/users/{uid}/role", response_model=UserProfile)
def set_role(uid: str, payload: RoleUpdate, _: CurrentUser = Depends(require_role(Role.ADMIN))):
    return user_service.set_user_role(uid, payload.role)
