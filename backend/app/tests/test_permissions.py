#!/usr/bin/env python3
"""
tests/test_permissions.py — Tests d'autorisation (services/permission_service.py).

Couvre : contrôle de rôle, accès administrateur (HR/ADMIN), accès aux ressources
propres, et calcul du périmètre de données par rôle (COLLAB / MANAGER / HR).
"""

import pytest
from fastapi import HTTPException

from app.services import permission_service as perm


def test_require_role_allows_and_denies():
    """require_role autorise un rôle listé et refuse les autres."""
    perm.require_role({"role": "HR"}, ["HR", "ADMIN"])  # ne lève pas
    with pytest.raises(HTTPException) as exc:
        perm.require_role({"role": "COLLAB"}, ["HR"])
    assert exc.value.status_code == 403


def test_require_admin():
    """require_admin réserve l'accès à HR/ADMIN."""
    perm.require_admin({"role": "HR"})
    perm.require_admin({"role": "ADMIN"})
    with pytest.raises(HTTPException):
        perm.require_admin({"role": "MANAGER"})


def test_require_own_resource():
    """Un utilisateur n'accède qu'à ses propres ressources (ADMIN excepté)."""
    perm.require_own_resource({"id": "u-1", "role": "COLLAB"}, "u-1")
    perm.require_own_resource({"id": "u-x", "role": "ADMIN"}, "u-1")  # ADMIN passe
    with pytest.raises(HTTPException):
        perm.require_own_resource({"id": "u-1", "role": "COLLAB"}, "u-2")


def test_check_collab_access():
    """Un COLLAB ne peut viser que ses propres données."""
    perm.check_collab_access({"id": "u-1", "role": "COLLAB"}, "u-1")
    with pytest.raises(HTTPException):
        perm.check_collab_access({"id": "u-1", "role": "COLLAB"}, "u-2")


def test_get_accessible_user_ids_scoping(make_user):
    """Le périmètre de données respecte strictement le rôle."""
    make_user(user_id="mgr-1", email="mgr@bmci.test", role="MANAGER")
    make_user(user_id="c-1", email="c1@bmci.test", role="COLLAB", manager_id="mgr-1")
    make_user(user_id="c-2", email="c2@bmci.test", role="COLLAB", manager_id="mgr-1")
    make_user(user_id="c-3", email="c3@bmci.test", role="COLLAB", manager_id="autre-mgr")

    # COLLAB : uniquement lui-même
    assert perm.get_accessible_user_ids({"id": "c-1", "role": "COLLAB"}) == ["c-1"]

    # MANAGER : uniquement son équipe
    team = set(perm.get_accessible_user_ids({"id": "mgr-1", "role": "MANAGER"}))
    assert team == {"c-1", "c-2"}
    assert "c-3" not in team

    # HR : tous les utilisateurs
    hr_scope = set(perm.get_accessible_user_ids({"id": "hr-x", "role": "HR"}))
    assert {"mgr-1", "c-1", "c-2", "c-3"}.issubset(hr_scope)
