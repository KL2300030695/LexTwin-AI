"""Tests for the Firebase-Auth-backed identity + role layer (app/auth,
app/routers/auth.py). Firebase itself (token verification, custom claims)
is mocked out -- these test our own dependency/role logic, not Firebase's
SDK. See test_audit_router.py / test_playbook_router.py for role-gating
verified against the actual protected endpoints."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import CurrentUser, Role, get_current_user, require_role
from app.main import app

client = TestClient(app)


def test_get_current_user_rejects_missing_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(credentials=None)
    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_invalid_token():
    fake_credentials = type("Creds", (), {"credentials": "not-a-real-token"})()
    with patch("app.auth.ensure_admin_app"), patch("firebase_admin.auth.verify_id_token", side_effect=Exception("bad token")):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=fake_credentials)
    assert exc_info.value.status_code == 401


def test_get_current_user_reads_role_from_custom_claims():
    fake_credentials = type("Creds", (), {"credentials": "a-valid-token"})()
    decoded = {"uid": "u1", "email": "a@b.com", "role": "approver"}
    with patch("app.auth.ensure_admin_app"), patch("firebase_admin.auth.verify_id_token", return_value=decoded):
        user = get_current_user(credentials=fake_credentials)
    assert user.uid == "u1"
    assert user.role == Role.APPROVER


def test_get_current_user_defaults_to_reviewer_when_role_claim_missing():
    fake_credentials = type("Creds", (), {"credentials": "a-valid-token"})()
    decoded = {"uid": "u1", "email": "a@b.com"}  # no "role" claim at all
    with patch("app.auth.ensure_admin_app"), patch("firebase_admin.auth.verify_id_token", return_value=decoded):
        user = get_current_user(credentials=fake_credentials)
    assert user.role == Role.REVIEWER


def test_require_role_accepts_exact_and_higher_roles():
    dependency = require_role(Role.APPROVER)
    assert dependency(user=CurrentUser(uid="u", role=Role.APPROVER)).role == Role.APPROVER
    assert dependency(user=CurrentUser(uid="u", role=Role.ADMIN)).role == Role.ADMIN


def test_require_role_rejects_lower_roles():
    dependency = require_role(Role.APPROVER)
    with pytest.raises(HTTPException) as exc_info:
        dependency(user=CurrentUser(uid="u", role=Role.REVIEWER))
    assert exc_info.value.status_code == 403


def test_me_endpoint_returns_authenticated_identity():
    # conftest.py's autouse fixture already overrides get_current_user with
    # an admin test identity for every router test.
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["role"] == "admin"


def test_reviewer_cannot_list_users_or_set_roles():
    """/users and /users/{uid}/role are admin-only -- conftest.py defaults
    every test to admin, so this downgrades to reviewer specifically to
    verify the 403, then restores the default for later tests."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uid="r", email="r@x.com", role=Role.REVIEWER)
    try:
        assert client.get("/api/auth/users").status_code == 403
        assert client.put("/api/auth/users/some-uid/role", json={"role": "admin"}).status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            uid="test-uid", email="test@example.com", role=Role.ADMIN
        )


def test_bootstrap_admin_rejected_when_an_admin_already_exists():
    with patch("app.services.user_service.count_admins", return_value=1):
        response = client.post("/api/auth/bootstrap-admin")
    assert response.status_code == 403


def test_bootstrap_admin_succeeds_when_no_admin_exists():
    with patch("app.services.user_service.count_admins", return_value=0), \
         patch("app.services.user_service.ensure_admin_app"), \
         patch("firebase_admin.auth.set_custom_user_claims") as mock_set, \
         patch("firebase_admin.auth.get_user") as mock_get:
        mock_get.return_value.uid = "test-uid"
        mock_get.return_value.email = "test@example.com"
        mock_get.return_value.custom_claims = {"role": "admin"}
        response = client.post("/api/auth/bootstrap-admin")

    assert response.status_code == 200
    mock_set.assert_called_once_with("test-uid", {"role": "admin"})


def test_protected_endpoint_401s_with_no_auth_override():
    """Sanity check that auth is really enforced, not just decorative:
    temporarily remove conftest's override and confirm the real dependency
    (which requires a bearer token) actually blocks the request."""
    app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.get("/api/auth/me")
        assert response.status_code == 401
    finally:
        # restore so subsequent tests in this process aren't affected --
        # conftest's fixture will also reset this after the test, but
        # belt-and-suspenders since we removed it mid-test here.
        from app.auth import Role as _Role

        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            uid="test-uid", email="test@example.com", role=_Role.ADMIN
        )
