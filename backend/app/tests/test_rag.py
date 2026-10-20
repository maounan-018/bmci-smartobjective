#!/usr/bin/env python3
"""
tests/test_rag.py — Socle RAG (sqlite-vec) : ingestion, recherche, périmètre.

Les embeddings sont monkeypatchés (vecteurs déterministes) : ces tests valident
la PLOMBERIE du RAG (stockage vec0, KNN, filtre de scope, suppression) SANS
dépendre d'Ollama — la suite reste hermétique et rapide. La qualité sémantique
réelle de bge-m3 est validée séparément (hors suite automatisée).
"""

import pytest

from app.services import rag_service


def _fake_embed(text: str):
    """Vecteur déterministe 1024-d : 1.0 à un index choisi par mot-clé.

    Permet de prédire exactement quel chunk est « le plus proche » sans modèle.
    """
    vec = [0.0] * 1024
    t = (text or "").lower()
    if "alpha" in t:
        vec[0] = 1.0
    elif "beta" in t:
        vec[1] = 1.0
    else:
        vec[2] = 1.0
    return vec


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    """Remplace les appels d'embedding par des vecteurs déterministes."""
    monkeypatch.setattr(rag_service, "embed_text", _fake_embed)
    monkeypatch.setattr(rag_service, "embed_batch", lambda texts: [_fake_embed(t) for t in texts])


@pytest.fixture
def cleanup_docs():
    """Supprime les documents créés par un test (chunks + vecteurs vec0)."""
    ids = []
    yield ids
    for doc_id in ids:
        rag_service.delete_document(doc_id)


def test_retrieve_returns_closest_chunk(cleanup_docs):
    a = rag_service.ingest_document("Sujet alpha : bancarisation des PME.", filename="a.txt", scope="GLOBAL")
    b = rag_service.ingest_document("Sujet beta : conformite reglementaire.", filename="b.txt", scope="GLOBAL")
    cleanup_docs += [a["id"], b["id"]]

    res = rag_service.retrieve("une question au sujet de alpha", scope="GLOBAL", top_k=1)
    assert res, "retrieve doit renvoyer un resultat"
    assert res[0]["document_id"] == a["id"]


def test_scope_isolation(cleanup_docs):
    g = rag_service.ingest_document("alpha contenu global", filename="g.txt", scope="GLOBAL")
    n = rag_service.ingest_document("alpha contenu entite nord", filename="n.txt", scope="NORD")
    cleanup_docs += [g["id"], n["id"]]

    # Une recherche GLOBAL ne doit JAMAIS renvoyer un document d'un autre périmètre.
    glob = rag_service.retrieve("alpha", scope="GLOBAL", top_k=10)
    assert all(r["scope"] != "NORD" for r in glob)

    # Dans son périmètre, le document restreint est bien visible.
    scoped = rag_service.retrieve("alpha", scope="NORD", top_k=10)
    assert any(r["document_id"] == n["id"] for r in scoped)


def test_delete_removes_document_and_vectors(cleanup_docs):
    d = rag_service.ingest_document("alpha a supprimer", filename="d.txt", scope="GLOBAL")
    removed = rag_service.delete_document(d["id"])
    assert removed >= 1

    # Le contenu supprimé ne doit plus ressortir d'une recherche.
    res = rag_service.retrieve("alpha", scope="GLOBAL", top_k=10)
    assert all(r["document_id"] != d["id"] for r in res)


# ============= API : base de connaissances (rag_controller) =============

def test_upload_allowed_for_collab_and_hr(client, make_user, auth_token):
    """Base de connaissances partagée : COLLAB et HR peuvent désormais téléverser (200)."""
    for role in ("COLLAB", "HR"):
        make_user(user_id=f"rag-{role.lower()}", email=f"rag-{role.lower()}@bmci.test", role=role)
        token = auth_token(f"rag-{role.lower()}")
        resp = client.post(
            "/api/rag/documents",
            files={"file": (f"{role.lower()}.txt", b"alpha contenu de test", "text/plain")},
            data={"scope": "GLOBAL"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"{role}: {resp.text}"


def test_upload_requires_authentication(client):
    """Un utilisateur non authentifié ne peut pas téléverser (401)."""
    resp = client.post(
        "/api/rag/documents",
        files={"file": ("note.txt", b"alpha contenu de test", "text/plain")},
        data={"scope": "GLOBAL"},
    )
    assert resp.status_code == 401


def test_upload_rejects_unsupported_format(client, make_user, auth_token):
    """Un format non supporté est refusé (400)."""
    make_user(user_id="mgr-rag2", email="mgrrag2@bmci.test", role="MANAGER")
    token = auth_token("mgr-rag2")
    resp = client.post(
        "/api/rag/documents",
        files={"file": ("image.png", b"\x89PNG\r\n", "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_upload_list_delete_cycle(client, make_user, auth_token):
    """Un MANAGER téléverse, retrouve dans la liste, puis supprime un document."""
    make_user(user_id="mgr-rag", email="mgrrag@bmci.test", role="MANAGER")
    token = auth_token("mgr-rag")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/rag/documents",
        files={"file": ("strategie.txt", b"alpha : axe strategique de test pour le rag", "text/plain")},
        data={"scope": "GLOBAL", "title": "Strategie test"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert doc["chunk_count"] >= 1
    doc_id = doc["id"]

    resp = client.get("/api/rag/documents", headers=headers)
    assert resp.status_code == 200
    assert any(d["id"] == doc_id for d in resp.json())

    resp = client.delete(f"/api/rag/documents/{doc_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
