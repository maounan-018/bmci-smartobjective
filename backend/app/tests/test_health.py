#!/usr/bin/env python3
"""
tests/test_health.py — Sondes de santé (liveness + readiness).

Vérifie /health (le process répond) et /health/ready (les dépendances réelles :
base de données = critique, Ollama = souple). En CI/tests, Ollama n'est pas lancé :
le statut peut être 'degraded' mais le code reste 200 tant que la DB répond — la
DB est la seule dépendance critique (sinon 503).
"""


def test_health_liveness(client):
    """GET /health : sonde de liveness, toujours 200 si le process répond."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_readiness_db_is_critical(client):
    """GET /health/ready : la DB répond -> 'ok' + HTTP 200 (Ollama souple)."""
    r = client.get("/health/ready")
    body = r.json()
    # La base de test est disponible -> check 'database' = ok.
    assert body["checks"]["database"] == "ok"
    # DB critique OK -> jamais 503 ; statut 'ready' (Ollama up) ou 'degraded' (Ollama down).
    assert r.status_code == 200
    assert body["status"] in ("ready", "degraded")
    assert "ollama" in body["checks"]
