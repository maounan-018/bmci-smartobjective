#!/usr/bin/env python3
"""
tests/test_auth_endpoints.py — Tests d'intégration des endpoints d'authentification.

Couvre : refus d'accès sans token (401), connexion (succès/échec), réhydratation
de session (/auth/me), et déclenchement du rate limiting (429).
Le backend reste la source de vérité pour la sécurité.
NB : l'inscription publique a été supprimée (création de compte via SSO/JIT ou seed).
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


def test_login_sets_httponly_cookie_and_me_works_via_cookie(client, make_user):
    """Le login pose un cookie de session ; /auth/me fonctionne via le cookie seul."""
    make_user(email="cookie@bmci.ma", password="GoodPass1!", role="HR")
    r = client.post("/api/auth/login", json={"email": "cookie@bmci.ma", "password": "GoodPass1!"})
    assert r.status_code == 200
    assert client.cookies.get("session")  # cookie de session posé
    # Pas d'en-tête Authorization : l'auth passe par le cookie.
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "cookie@bmci.ma"


def test_cookie_post_requires_csrf(client, make_user):
    """Une requête mutante authentifiée par cookie exige le jeton CSRF."""
    make_user(email="csrf@bmci.ma", password="GoodPass1!")
    client.post("/api/auth/login", json={"email": "csrf@bmci.ma", "password": "GoodPass1!"})
    # POST sans en-tête CSRF -> 403
    assert client.post("/api/auth/logout").status_code == 403
    # POST avec le bon en-tête CSRF (= valeur du cookie csrf_token) -> 200
    csrf = client.cookies.get("csrf_token")
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200


def test_login_rejects_invalid_email_format(client):
    """Un email mal formé est rejeté par la validation (422), pas traité comme un login."""
    resp = client.post("/api/auth/login", json={"email": "pas-un-email", "password": "x"})
    assert resp.status_code == 422


def test_login_rejects_oversize_password(client):
    """Un mot de passe géant est rejeté (borne anti-DoS PBKDF2)."""
    resp = client.post("/api/auth/login",
                       json={"email": "user@bmci.ma", "password": "a" * 200})
    assert resp.status_code == 422


def test_login_rate_limiting(client, make_user):
    """Après plusieurs échecs, le compte est temporairement bloqué (429)."""
    make_user(email="rl@bmci.test", password="GoodPass1!")
    for _ in range(5):
        client.post("/api/auth/login",
                    json={"email": "rl@bmci.test", "password": "WRONG"})
    resp = client.post("/api/auth/login",
                       json={"email": "rl@bmci.test", "password": "GoodPass1!"})
    assert resp.status_code == 429
