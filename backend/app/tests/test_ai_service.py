#!/usr/bin/env python3
"""
tests/test_ai_service.py — Robustesse de l'appel IA (réessai sur réponse vide).

Couvre le correctif du cas « {} » : quand le modèle local renvoie un JSON vide ou
non parsable, `call_ollama` RÉESSAIE (settings.AI_MAX_ATTEMPTS) au lieu de retomber
directement sur l'analyse dégradée « tout faux, sans reformulation ».
Ollama est simulé (monkeypatch sur `_post_to_ollama`) : aucun appel réseau réel.
"""

from app.services import ai_service

_VALID_SMART = (
    '{"S":true,"M":true,"A":true,"R":true,"T":true,"overall":true,'
    '"confidence":0.9,"issues":[],"rewrite_fr":"Reformulé FR","rewrite_en":"Rewritten EN"}'
)


def test_call_ollama_retries_until_valid(monkeypatch):
    """Réponse vide au 1er essai, valide au 2e -> call_ollama renvoie la 2e."""
    seq = iter(["{}", _VALID_SMART])
    calls = {"n": 0}

    def fake_post(prompt, system):
        calls["n"] += 1
        return next(seq)

    monkeypatch.setattr(ai_service, "_post_to_ollama", fake_post)
    res = ai_service.call_ollama("p", "s", is_valid=ai_service._smart_response_ok)
    assert calls["n"] == 2          # a bien réessayé une fois
    assert res["S"] is True
    assert res["rewrite_fr"] == "Reformulé FR"


def test_call_ollama_returns_empty_after_exhausting_retries(monkeypatch):
    """Toujours {} -> dict vide renvoyé (l'appelant appliquera ses valeurs par défaut)."""
    monkeypatch.setattr(ai_service, "_post_to_ollama", lambda p, s: "{}")
    res = ai_service.call_ollama("p", "s", is_valid=ai_service._smart_response_ok)
    assert res == {}


def test_analyze_smart_uses_retry_result(monkeypatch):
    """Le {} initial est ignoré : analyze_smart_internal renvoie la vraie analyse."""
    seq = iter(["{}", _VALID_SMART])
    monkeypatch.setattr(ai_service, "_post_to_ollama", lambda p, s: next(seq))
    res = ai_service.analyze_smart_internal(
        "Augmenter les ventes de 10% d'ici le 31/12/2026", "desc"
    )
    assert res["rewrite_fr"] == "Reformulé FR"
    assert res["overall"] is True


def test_analyze_smart_falls_back_to_defaults_when_always_empty(monkeypatch):
    """Toujours {} -> pas de crash : structure complète + repli (overall False + issues)."""
    monkeypatch.setattr(ai_service, "_post_to_ollama", lambda p, s: "{}")
    res = ai_service.analyze_smart_internal("Objectif flou", "desc")
    assert {"S", "M", "A", "R", "T", "overall", "issues", "rewrite_fr"}.issubset(res)
    assert res["overall"] is False
    assert isinstance(res["issues"], list) and len(res["issues"]) >= 1
