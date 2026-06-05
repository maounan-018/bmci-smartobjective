#!/usr/bin/env python3
"""
tests/test_security.py — Tests des primitives de sécurité (core/security.py).

Couvre : hachage PBKDF2, vérification à temps constant, migration depuis le
format SHA-256 legacy, unicité des tokens et limitation anti brute-force.
"""

import hashlib

from app.core import security


def test_hash_password_roundtrip():
    """Un mot de passe haché doit se vérifier correctement."""
    h = security.hash_password("MonMotDePasse!")
    assert h.startswith("pbkdf2_sha256$")
    assert security.verify_password("MonMotDePasse!", h) is True
    assert security.verify_password("mauvais", h) is False


def test_hash_is_salted():
    """Deux hachages du même mot de passe diffèrent (sel aléatoire)."""
    assert security.hash_password("identique") != security.hash_password("identique")


def test_hash_never_contains_plaintext():
    """Le hash ne doit jamais contenir le mot de passe en clair."""
    secret = "SuperSecretBancaire"
    assert secret not in security.hash_password(secret)


def test_legacy_sha256_verification_and_rehash():
    """Le format SHA-256 simple doit rester vérifiable et être marqué à migrer."""
    legacy = hashlib.sha256("legacypass".encode("utf-8")).hexdigest()
    assert security.needs_rehash(legacy) is True
    assert security.verify_password("legacypass", legacy) is True
    # Le nouveau format ne doit jamais être considéré comme legacy
    assert security.needs_rehash(security.hash_password("x")) is False


def test_verify_password_handles_empty():
    """Un hash vide ne valide jamais un mot de passe."""
    assert security.verify_password("anything", "") is False


def test_generate_token_unique_and_long():
    """Les tokens doivent être uniques et suffisamment longs."""
    tokens = {security.generate_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(len(t) >= 32 for t in tokens)


def test_rate_limiting_blocks_after_max_attempts():
    """Après MAX_LOGIN_ATTEMPTS échecs, l'identifiant est bloqué."""
    ident = "brute@bmci.test"
    security._failed_login_attempts.clear()
    assert security.is_login_allowed(ident) is True
    for _ in range(security.settings.MAX_LOGIN_ATTEMPTS):
        security.record_failed_login(ident)
    assert security.is_login_allowed(ident) is False
    # La réinitialisation débloque l'identifiant
    security.reset_login_attempts(ident)
    assert security.is_login_allowed(ident) is True


def test_request_size_limit_rejects_oversize_upload(client):
    """Une requete depassant MAX_REQUEST_SIZE_MB doit etre rejetee en 413.

    Conftest fixe la limite a 5 Mo : on envoie 6 Mo, on doit recevoir 413
    avant meme que l'endpoint ne soit atteint. Le middleware regarde
    Content-Length avant toute lecture du body — defense rapide DoS upload.
    """
    big_payload = b"0" * (6 * 1024 * 1024)  # 6 Mo > 5 Mo
    resp = client.post("/api/auth/register", content=big_payload)
    assert resp.status_code == 413
    detail = resp.json().get("detail", "").lower()
    assert "max" in detail or "volumineuse" in detail
