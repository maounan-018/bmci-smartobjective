#!/usr/bin/env python3
"""
tests/test_auth_endpoints.py — Tests d'intégration des endpoints d'authentification.

Couvre : refus d'accès sans token (401), connexion (succès/échec), réhydratation
de session (/auth/me), inscription (/auth/register), et déclenchement du rate
limiting (429). Le backend reste la source de vérité pour la sécurité.
"""


def test_protected_endpoint_without_token_returns_401(client):
    """Un endpoint protégé doit refuser l'accès sans token."""
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_protected_business_endpoint_without_token_returns_401(client):
    """Les endpoints métier exigent aussi un token (sécurité côté backend)."""
    resp = client.get("/api/manager/objectives")
    assert resp.status_code == 401


def test_health_is_public(client):
    """La sonde /health reste accessible sans authentification."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_login_success(client, make_user):
    """Une connexion valide retourne un token et le profil utilisateur."""
    make_user(email="login@bmci.test", password="GoodPass1!", role="HR")
    resp = client.post("/api/auth/login",
                       json={"email": "login@bmci.test", "password": "GoodPass1!"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["token"]
    assert body["user"]["role"] == "HR"
    # Le mot de passe ne doit jamais être renvoyé
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_login_wrong_password(client, make_user):
    """Un mot de passe incorrect renvoie 401."""
    make_user(email="wrong@bmci.test", password="GoodPass1!")
    resp = client.post("/api/auth/login",
                       json={"email": "wrong@bmci.test", "password": "BadPass"})
    assert resp.status_code == 401


def test_me_with_valid_token(client, make_user, auth_token):
    """/auth/me retourne le profil pour un token valide."""
    make_user(user_id="u-me", email="me@bmci.test")
    token = auth_token("u-me")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "me@bmci.test"


def test_register_collab_requires_manager(client):
    """Un COLLAB sans manager doit être refusé (400)."""
    resp = client.post("/api/auth/register", json={
        "email": "newcollab@bmci.test", "password": "Pass1234!",
        "name": "Nouveau",
    })
    assert resp.status_code == 400


def test_register_success(client, make_user):
    """Inscription d'un COLLAB rattaché à un manager existant."""
    make_user(user_id="mgr-9", email="mgr9@bmci.test", role="MANAGER")
    resp = client.post("/api/auth/register", json={
        "email": "fresh@bmci.test", "password": "Pass1234!",
        "name": "Fresh", "manager_id": "mgr-9",
    })
    assert resp.status_code == 200
    assert resp.json()["token"]


def test_register_hr_is_allowed(client):
    """L'inscription publique d'un HR est autorisée (sans manager_id)."""
    resp = client.post("/api/auth/register", json={
        "email": "new-hr@bmci.test", "password": "Pass1234!",
        "name": "Nouveau RH", "role": "HR",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["role"] == "HR"
    assert body["user"]["manager_id"] is None
    assert body["token"]


def test_register_manager_is_allowed(client):
    """L'inscription publique d'un MANAGER est autorisée (sans manager_id)."""
    resp = client.post("/api/auth/register", json={
        "email": "new-mgr@bmci.test", "password": "Pass1234!",
        "name": "Nouveau Manager", "role": "MANAGER",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["role"] == "MANAGER"
    assert body["user"]["manager_id"] is None
    assert body["token"]


def test_register_unknown_role_falls_back_to_collab(client, make_user):
    """Toute valeur de rôle inconnue (ADMIN, ROOT...) est ramenée à COLLAB."""
    make_user(user_id="mgr-12", email="mgr12@bmci.test", role="MANAGER")
    resp = client.post("/api/auth/register", json={
        "email": "evil-admin@bmci.test", "password": "Pass1234!",
        "name": "Evil3", "role": "ADMIN", "manager_id": "mgr-12",
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "COLLAB"


def test_login_rate_limiting(client, make_user):
    """Après plusieurs échecs, le compte est temporairement bloqué (429)."""
    make_user(email="rl@bmci.test", password="GoodPass1!")
    for _ in range(5):
        client.post("/api/auth/login",
                    json={"email": "rl@bmci.test", "password": "WRONG"})
    resp = client.post("/api/auth/login",
                       json={"email": "rl@bmci.test", "password": "GoodPass1!"})
    assert resp.status_code == 429
