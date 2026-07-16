"""Tests app/services/user_service.py -- role management via Firebase Auth
custom claims. firebase_admin.auth itself is mocked; this tests our own
logic (bootstrap-admin's zero-admins check, role parsing) not Firebase's SDK.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.auth import CurrentUser, Role
from app.services import user_service


def _fake_user_record(uid, email, role=None):
    record = MagicMock()
    record.uid = uid
    record.email = email
    record.custom_claims = {"role": role} if role else None
    return record


def test_list_users_parses_role_from_custom_claims():
    records = [_fake_user_record("u1", "a@b.com", "admin"), _fake_user_record("u2", "c@d.com", None)]
    with patch("app.services.user_service.ensure_admin_app"), \
         patch("firebase_admin.auth.list_users") as mock_list:
        mock_list.return_value.iterate_all.return_value = records
        users = user_service.list_users()

    assert users[0].role == Role.ADMIN
    assert users[1].role == Role.REVIEWER  # no claim set -- defaults to the least-privileged role


def test_set_user_role_calls_set_custom_user_claims():
    with patch("app.services.user_service.ensure_admin_app"), \
         patch("firebase_admin.auth.set_custom_user_claims") as mock_set, \
         patch("firebase_admin.auth.get_user", return_value=_fake_user_record("u1", "a@b.com", "approver")):
        result = user_service.set_user_role("u1", Role.APPROVER)

    mock_set.assert_called_once_with("u1", {"role": "approver"})
    assert result.role == Role.APPROVER


def test_bootstrap_first_admin_succeeds_when_no_admins_exist():
    with patch("app.services.user_service.ensure_admin_app"), \
         patch("firebase_admin.auth.list_users") as mock_list, \
         patch("firebase_admin.auth.set_custom_user_claims") as mock_set, \
         patch("firebase_admin.auth.get_user", return_value=_fake_user_record("u1", "a@b.com", "admin")):
        mock_list.return_value.iterate_all.return_value = []  # zero users, so zero admins
        result = user_service.bootstrap_first_admin(CurrentUser(uid="u1", email="a@b.com"))

    mock_set.assert_called_once_with("u1", {"role": "admin"})
    assert result.role == Role.ADMIN


def test_bootstrap_first_admin_rejected_once_an_admin_exists():
    with patch("app.services.user_service.ensure_admin_app"), \
         patch("firebase_admin.auth.list_users") as mock_list:
        mock_list.return_value.iterate_all.return_value = [_fake_user_record("existing", "e@x.com", "admin")]
        with pytest.raises(PermissionError):
            user_service.bootstrap_first_admin(CurrentUser(uid="u2", email="b@c.com"))
