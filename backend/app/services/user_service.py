"""User/role management via Firebase Auth custom claims -- no separate
Firestore `users` collection, since Firebase Auth is already the source of
truth for every user account. See app/auth/__init__.py for how the role
claim gets read back out of the ID token on each request."""
from __future__ import annotations

from app.auth import CurrentUser, Role, ensure_admin_app
from app.models.user import UserProfile


def _to_profile(user_record) -> UserProfile:
    claims = user_record.custom_claims or {}
    raw_role = claims.get("role", Role.REVIEWER.value)
    try:
        role = Role(raw_role)
    except ValueError:
        role = Role.REVIEWER
    return UserProfile(uid=user_record.uid, email=user_record.email, role=role)


def list_users() -> list[UserProfile]:
    ensure_admin_app()
    from firebase_admin import auth as firebase_auth

    return [_to_profile(u) for u in firebase_auth.list_users().iterate_all()]


def set_user_role(uid: str, role: Role) -> UserProfile:
    ensure_admin_app()
    from firebase_admin import auth as firebase_auth

    firebase_auth.set_custom_user_claims(uid, {"role": role.value})
    return _to_profile(firebase_auth.get_user(uid))


def count_admins() -> int:
    ensure_admin_app()
    from firebase_admin import auth as firebase_auth

    return sum(1 for u in firebase_auth.list_users().iterate_all() if (u.custom_claims or {}).get("role") == Role.ADMIN.value)


def bootstrap_first_admin(user: CurrentUser) -> UserProfile:
    """Promotes `user` to admin, but only if the system currently has zero
    admins -- solves the chicken-and-egg problem of "you need an admin to
    assign admins, but no admin exists yet" without a hardcoded backdoor
    credential. Once one admin exists, this always 403s (see the router)."""
    if count_admins() > 0:
        raise PermissionError("An admin already exists; ask them to assign your role instead.")
    return set_user_role(user.uid, Role.ADMIN)
