#!/usr/bin/env python3
"""
tests/conftest.py — Configuration et fixtures partagées pour la suite de tests.

RÔLE
    Isole les tests de la base de production : crée une base SQLite temporaire,
    y installe le schéma complet via l'ORM (init_db), puis expose un client de
    test FastAPI et des utilitaires de création de comptes (via SQLAlchemy).

IMPORTANT
    Les variables d'environnement (DATABASE_PATH, secrets de seed) sont
    positionnées AVANT tout import de l'application, car `settings` et le moteur
    SQLAlchemy lisent l'environnement une seule fois, au moment de l'import.
"""

import os
import tempfile

import pytest

# 1. Base temporaire + environnement de test — AVANT d'importer l'application
_TMP_DB = os.path.join(tempfile.gettempdir(), "objectifsmart_test.db")
os.environ["DATABASE_PATH"] = _TMP_DB
os.environ["MAX_LOGIN_ATTEMPTS"] = "5"
os.environ["LOGIN_LOCKOUT_MINUTES"] = "15"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"
# Limite reduite pour pouvoir tester le rejet 413 sans envoyer 20 Mo
os.environ["MAX_REQUEST_SIZE_MB"] = "5"
# Pas de seeding pendant les tests : isolation stricte des donnees.
os.environ["SEED_DEMO_ACCOUNTS"] = "false"

# Supprimer une éventuelle base de test résiduelle
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.database.init_db import init_db  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402
from app.core import security  # noqa: E402
from app.models import (  # noqa: E402
    User, Session as SessionModel, SsoCode, Objective, CompanyObjective, HRImport, AuditLog,
    HRAnalysisResult, ManagerAnalysisResult, CollabAnalysisResult,
)

# Tables vidées entre chaque test pour garantir l'isolation
_CLEANED_MODELS = [
    SsoCode, SessionModel, AuditLog, Objective, CompanyObjective, HRImport,
    HRAnalysisResult, ManagerAnalysisResult, CollabAnalysisResult, User,
]


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    """Prépare la base temporaire (schéma ORM) une fois pour la session."""
    init_db()
    yield
    if os.path.exists(_TMP_DB):
        try:
            os.remove(_TMP_DB)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def _clean_tables():
    """Vide les tables avant chaque test pour garantir l'isolation."""
    db = SessionLocal()
    try:
        for model in _CLEANED_MODELS:
            db.query(model).delete()
        db.commit()
    finally:
        db.close()
    # Réinitialiser le compteur anti brute-force (état en mémoire)
    security._failed_login_attempts.clear()
    yield


@pytest.fixture
def client():
    """Client HTTP de test pour l'application FastAPI."""
    return TestClient(app)


@pytest.fixture
def make_user():
    """
    Fabrique un utilisateur en base (mot de passe haché) via l'ORM.
    Retourne le dict de l'utilisateur (mot de passe en clair inclus pour le test).
    """
    def _make(user_id="u-1", email="user@bmci.test", password="Secret123!",
              name="Test User", role="COLLAB", manager_id=None):
        db = SessionLocal()
        try:
            db.add(User(
                id=user_id, email=email, password_hash=security.hash_password(password),
                name=name, role=role, manager_id=manager_id,
            ))
            db.commit()
        finally:
            db.close()
        return {"id": user_id, "email": email, "password": password,
                "name": name, "role": role, "manager_id": manager_id}
    return _make


@pytest.fixture
def auth_token():
    """Crée une session valide pour un utilisateur donné et retourne le token."""
    from datetime import datetime, timedelta

    def _token(user_id="u-1"):
        token = security.generate_token()
        expires = (datetime.now() + timedelta(hours=1)).isoformat()
        db = SessionLocal()
        try:
            # On stocke le HASH (comme en prod) ; le token brut est renvoyé à l'appelant.
            db.add(SessionModel(token=security.hash_token(token), user_id=user_id, expires_at=expires))
            db.commit()
        finally:
            db.close()
        return token
    return _token
