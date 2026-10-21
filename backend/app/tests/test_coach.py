#!/usr/bin/env python3
"""
tests/test_coach.py — Coach IA conversationnel (/api/chat-coach).

L'appel Ollama (`call_ollama_chat`) et la récupération RAG (`_retrieve_coach_context`)
sont monkeypatchés : ces tests valident le routage, la garde de rôle, la
validation Pydantic et l'extraction du marqueur final SANS dépendre d'Ollama.
"""

import pytest
from app.services import ai_service


@pytest.fixture(autouse=True)
def _stub_coach(monkeypatch):
    """Neutralise le RAG et Ollama dans les tests (réponse canée déterministe)."""
    monkeypatch.setattr(
        ai_service, "_retrieve_coach_context", lambda messages, uploaded_by=None: None
    )
    monkeypatch.setattr(
        ai_service,
        "call_ollama_chat",
        lambda messages, extra_context=None: "Bonjour ! Quel est votre objectif principal ?",
    )
    # Revalidation SMART de l'objectif final neutralisée (sinon appel Ollama réel).
    monkeypatch.setattr(
        ai_service,
        "analyze_smart_internal",
        lambda title, description="": {
            "S": True,
            "M": True,
            "A": True,
            "R": True,
            "T": True,
            "overall": True,
            "confidence": 0.9,
            "issues": [],
        },
    )


def _post(client, token, content="Je veux ameliorer la satisfaction client"):
    return client.post(
        "/api/chat-coach",
        json={"messages": [{"role": "user", "content": content}]},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_chat_coach_allows_manager(client, make_user, auth_token):
    make_user(user_id="mgr-coach", email="mgrcoach@bmci.test", role="MANAGER")
    resp = _post(client, auth_token("mgr-coach"))
    assert resp.status_code == 200
    assert resp.json()["reply"]


def test_chat_coach_allows_collab(client, make_user, auth_token):
    make_user(user_id="collab-coach", email="collabcoach@bmci.test", role="COLLAB")
    resp = _post(client, auth_token("collab-coach"))
    assert resp.status_code == 200


def test_chat_coach_allows_hr(client, make_user, auth_token):
    make_user(user_id="hr-coach", email="hrcoach@bmci.test", role="HR")
    resp = _post(client, auth_token("hr-coach"))
    assert resp.status_code == 200


def test_chat_coach_rejects_non_user_last_message(client, make_user, auth_token):
    make_user(user_id="mgr-coach3", email="mgrcoach3@bmci.test", role="MANAGER")
    resp = client.post(
        "/api/chat-coach",
        json={"messages": [{"role": "assistant", "content": "bonjour"}]},
        headers={"Authorization": f"Bearer {auth_token('mgr-coach3')}"},
    )
    assert resp.status_code == 422  # doit se terminer par un message user


def test_chat_coach_extracts_final_marker(client, make_user, auth_token, monkeypatch):
    monkeypatch.setattr(
        ai_service,
        "call_ollama_chat",
        lambda messages,
        extra_context=None: 'Parfait, voici la synthese. {"final_objective": "Augmenter le NPS de 10 points d ici dec 2026", "ready": true}',
    )
    make_user(user_id="mgr-coach4", email="mgrcoach4@bmci.test", role="MANAGER")
    resp = _post(client, auth_token("mgr-coach4"), content="termine")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert "NPS" in data["final_objective"]
    # Le marqueur JSON ne doit pas rester dans le texte affiché.
    assert "final_objective" not in data["reply"]
    # L'objectif final est revalidé par le pipeline SMART (présent dans la réponse).
    assert data["smart_validation"] is not None and "overall" in data["smart_validation"]
