#!/usr/bin/env python3
"""
tests/test_ai_rate_limit.py — Quota d'appels IA (anti-saturation d'Ollama).

Vérifie que le rate limiting (services/ai_rate_limit_service, état en base
`ai_calls`) bloque après AI_RATE_LIMIT_MAX appels, qu'il est PAR utilisateur, et
que l'endpoint IA renvoie 429 AVANT de solliciter Ollama quand le quota est plein.
"""

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services import ai_rate_limit_service


def test_ai_rate_limit_blocks_after_max():
    """Après AI_RATE_LIMIT_MAX appels, l'utilisateur est bloqué (429)."""
    uid = "u-ai-unit"
    for _ in range(settings.AI_RATE_LIMIT_MAX):
        ai_rate_limit_service.enforce(uid)  # sous le quota -> OK
    with pytest.raises(HTTPException) as exc:
        ai_rate_limit_service.enforce(uid)
    assert exc.value.status_code == 429


def test_ai_rate_limit_is_per_user():
    """Le quota d'un utilisateur n'affecte pas les autres."""
    saturated, other = "u-ai-a", "u-ai-b"
    for _ in range(settings.AI_RATE_LIMIT_MAX):
        ai_rate_limit_service.enforce(saturated)
    # `other` n'a encore rien consommé : son appel doit passer.
    ai_rate_limit_service.enforce(other)  # ne doit pas lever


def test_ai_endpoint_returns_429_when_over_quota(client, make_user, auth_token):
    """L'endpoint IA renvoie 429 dès que le quota est plein, SANS appeler Ollama."""
    make_user(user_id="u-ai-http", email="aihttp@bmci.test", role="COLLAB")
    token = auth_token("u-ai-http")

    # On remplit le quota directement (sans passer par Ollama).
    for _ in range(settings.AI_RATE_LIMIT_MAX):
        ai_rate_limit_service.enforce("u-ai-http")

    # La requête HTTP suivante est rejetée par la dépendance AVANT le corps de la
    # route : aucune connexion à Ollama n'est tentée.
    resp = client.post(
        "/api/analyze-smart",
        json={"title": "Objectif test", "description": "desc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 429
    assert "max" in resp.json().get("detail", "").lower()
