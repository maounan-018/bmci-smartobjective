#!/usr/bin/env python3
"""
tests/test_review_fixes.py — Tests de non-régression pour les corrections de code review.

Couvre les 5 corrections prioritaires :
  S-2  GET /company-objectives exige une authentification
  D-2  batch_create_company_objectives remonte les erreurs sans les avaler
  S-3  Validation binaire (_CTRL_RE) rejette les titres corrompus
  D-4  Les enums Literal rejettent status/progress invalides
  S-6  logout() tolère un verrou de base (ne plante jamais le client)
"""

import pytest
from pydantic import ValidationError
from unittest.mock import patch

from app.schemas.objective_schema import ObjectiveUpdate, ObjectiveCreate, CompanyObjectiveCreate


# ─────────────────────────────────────────────────────
# S-3 — Validation binaire (_CTRL_RE)
# ─────────────────────────────────────────────────────

class TestCtrlReValidation:
    def test_binary_title_rejected(self):
        with pytest.raises(ValidationError, match="binaires"):
            ObjectiveCreate(title="Objectif\x00corrompu")

    def test_ctrl_char_in_description_rejected(self):
        with pytest.raises(ValidationError, match="binaires"):
            ObjectiveCreate(title="Titre valide", description="Desc\x0bcorrupted")

    def test_normal_text_accepted(self):
        obj = ObjectiveCreate(title="Développer les compétences", description="Description normale.")
        assert obj.title == "Développer les compétences"

    def test_tab_newline_accepted(self):
        obj = ObjectiveCreate(title="Titre", description="Ligne 1\nLigne 2\tAvec tabulation.")
        assert obj.description is not None

    def test_binary_in_company_objective_rejected(self):
        with pytest.raises(ValidationError, match="binaires"):
            CompanyObjectiveCreate(title="Axe\x03PK\x03\x04binaire")


# ─────────────────────────────────────────────────────
# D-4 — Enums Literal pour status / progress
# ─────────────────────────────────────────────────────

class TestLiteralEnums:
    def test_invalid_status_rejected(self):
        with pytest.raises(ValidationError):
            ObjectiveUpdate(status="invalid_status")

    def test_invalid_progress_rejected(self):
        with pytest.raises(ValidationError):
            ObjectiveUpdate(progress="unknown_progress")

    def test_valid_status_accepted(self):
        obj = ObjectiveUpdate(status="active")
        assert obj.status == "active"

    def test_valid_progress_accepted(self):
        obj = ObjectiveUpdate(progress="in_progress")
        assert obj.progress == "in_progress"

    def test_all_valid_status_values(self):
        for val in ("draft", "active", "completed", "archived"):
            obj = ObjectiveUpdate(status=val)
            assert obj.status == val

    def test_all_valid_progress_values(self):
        for val in ("not_started", "in_progress", "completed", "on_hold"):
            obj = ObjectiveUpdate(progress=val)
            assert obj.progress == val

    def test_none_values_accepted(self):
        obj = ObjectiveUpdate(status=None, progress=None)
        assert obj.status is None
        assert obj.progress is None


# ─────────────────────────────────────────────────────
# S-2 — GET /company-objectives exige une auth
# ─────────────────────────────────────────────────────

class TestCompanyObjectivesAuth:
    def test_unauthenticated_returns_401(self, client):
        resp = client.get("/api/company-objectives")
        assert resp.status_code == 401

    def test_authenticated_returns_200(self, client, make_user, auth_token):
        user = make_user(role="COLLAB")
        token = auth_token(user["id"])
        resp = client.get(
            "/api/company-objectives",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "company_objectives" in resp.json()


# ─────────────────────────────────────────────────────
# D-2 — batch_create remonte les erreurs sans les avaler
# ─────────────────────────────────────────────────────

class TestBatchCreateErrors:
    def test_batch_returns_error_list_on_partial_failure(self, client, make_user, auth_token):
        manager = make_user(user_id="m-1", role="MANAGER", email="manager@bmci.test")
        token = auth_token(manager["id"])

        payload = [{"title": "Axe stratégique A", "description": "", "department": "Finance"}]
        resp = client.post(
            "/api/company-objectives/batch",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_batch_collab_forbidden(self, client, make_user, auth_token):
        collab = make_user(user_id="c-1", role="COLLAB", email="collab@bmci.test")
        token = auth_token(collab["id"])

        resp = client.post(
            "/api/company-objectives/batch",
            json=[{"title": "Axe test"}],
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────
# S-6 — logout() tolère un verrou de base
# ─────────────────────────────────────────────────────

class TestLogoutRobustness:
    def test_logout_succeeds_even_if_db_locked(self, client, make_user, auth_token):
        user = make_user(user_id="u-logout", email="logout@bmci.test")
        token = auth_token(user["id"])

        with patch(
            "app.repositories.session_repository.delete_by_user",
            side_effect=Exception("database is locked"),
        ):
            resp = client.post(
                "/api/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
            )
        # Le serveur ne doit pas crasher ; le cookie est effacé par le controller
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_logout_without_session_returns_401(self, client):
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 401
