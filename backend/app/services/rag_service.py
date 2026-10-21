#!/usr/bin/env python3
"""
services/rag_service.py — Orchestration du RAG (base de connaissances).

RÔLE
    Pivot de la recherche sémantique de l'assistant. Deux opérations :
      - `ingest_document` : texte -> découpe en chunks -> embeddings (bge-m3) ->
        stockage (table relationnelle `rag_chunks` + table vectorielle vec0).
      - `retrieve` : question -> embedding -> plus proches voisins (KNN vec0) ->
        jointure aux chunks, filtrés par périmètre (scope).
    Plus la gestion des fiches documents (`list_documents`, `delete_document`).

SÉCURITÉ
    `retrieve` filtre par `scope` : un document d'un périmètre donné n'est jamais
    renvoyé hors de ce périmètre (les documents GLOBAL restent visibles par tous).
    Tout est local (embeddings Ollama + SQLite) : aucune donnée ne sort (CNDP).

EMPLACEMENT MVC
    Couche "services" : logique métier RAG, sans route HTTP.
"""

import json
import logging
import re
from datetime import datetime

from app.database.session import db_session
from app.models import RagChunk, RagDocument
from app.services.embedding_service import embed_batch, embed_text
from sqlalchemy import text

logger = logging.getLogger(__name__)


# ============= DÉCOUPAGE =============


def _chunk_text(content: str, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    """Découpe un texte en passages d'environ `max_chars` caractères.

    On respecte d'abord les paragraphes (double saut de ligne) ; un paragraphe
    trop long est re-découpé en fenêtres avec un léger recouvrement (`overlap`)
    pour ne pas trancher une idée net sans transition.
    """
    content = (content or "").strip()
    if not content:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    chunks: list[str] = []
    buffer = ""

    def flush() -> None:
        nonlocal buffer
        if buffer.strip():
            chunks.append(buffer.strip())
        buffer = ""

    for para in paragraphs:
        if len(para) > max_chars:
            flush()
            start = 0
            step = max(1, max_chars - overlap)
            while start < len(para):
                piece = para[start : start + max_chars].strip()
                if piece:
                    chunks.append(piece)
                start += step
            continue
        if buffer and len(buffer) + len(para) + 1 > max_chars:
            flush()
        buffer = f"{buffer}\n{para}".strip() if buffer else para
    flush()
    return [c for c in chunks if c]


# ============= INGESTION =============


def ingest_document(
    content: str,
    *,
    filename: str,
    title: str | None = None,
    scope: str = "GLOBAL",
    source_type: str = "manual",
    uploaded_by: str | None = None,
) -> dict:
    """Indexe un document : découpe, embeddings, stockage (chunks + vecteurs).

    Renvoie la fiche du document créé. Lève ValueError si le contenu est vide.
    """
    chunks = _chunk_text(content)
    if not chunks:
        raise ValueError("Aucun contenu exploitable à indexer.")

    # Embeddings AVANT la transaction DB : si Ollama échoue, on n'écrit rien.
    vectors = embed_batch(chunks)

    now = datetime.now().isoformat()
    with db_session() as db:
        doc = RagDocument(
            filename=filename,
            title=(title or filename),
            source_type=source_type,
            scope=scope,
            status="ready",
            chunk_count=len(chunks),
            uploaded_by=uploaded_by,
            created_at=now,
        )
        db.add(doc)
        db.flush()  # assigne doc.id

        for index, (chunk_text, vector) in enumerate(zip(chunks, vectors, strict=False)):
            chunk = RagChunk(
                document_id=doc.id,
                chunk_index=index,
                text=chunk_text,
                scope=scope,
            )
            db.add(chunk)
            db.flush()  # assigne chunk.id (== rowid de la table vectorielle)
            # vec0 n'est pas géré par l'ORM : insertion en SQL brut. Le vecteur est
            # passé en texte JSON (sqlite-vec l'accepte) ; rowid == id du chunk.
            db.execute(
                text("INSERT INTO vec_rag_chunks(rowid, embedding) VALUES (:rid, :emb)"),
                {"rid": chunk.id, "emb": json.dumps(vector)},
            )

        info = {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "scope": doc.scope,
            "source_type": doc.source_type,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "created_at": doc.created_at,
        }
        logger.info(
            "RAG: document '%s' indexé (%d chunks, scope=%s).",
            doc.title,
            doc.chunk_count,
            doc.scope,
        )
        return info


# ============= RECHERCHE =============


def retrieve(
    query: str,
    *,
    scope: str = "GLOBAL",
    top_k: int = 4,
    max_distance: float | None = None,
    uploaded_by: str | None = None,
) -> list[dict]:
    """Retourne les passages les plus proches sémantiquement de `query`.

    - Filtre de périmètre : seuls les chunks de `scope` ou de scope GLOBAL.
    - `uploaded_by` (optionnel) : restreint aux documents téléversés par cet
      utilisateur (base de connaissances PRIVÉE : chacun n'interroge que ses
      propres documents). None = aucun filtre de propriété.
    - `max_distance` (optionnel) = SEUIL : au-delà, un passage est jugé hors
      sujet et écarté (permet de répondre « rien trouvé » plutôt qu'un faux
      positif). Sans seuil, on renvoie les `top_k` plus proches tels quels.
    """
    if not query or not query.strip():
        return []

    qvector = embed_text(query)
    qjson = json.dumps(qvector)

    # On sur-échantillonne le KNN (overfetch) PUIS on filtre par périmètre, car le
    # filtre scope porte sur la table relationnelle, pas sur l'index vectoriel.
    overfetch = max(top_k * 5, 20)
    top_k = max(1, top_k)

    sql = text(f"""
        WITH knn AS (
            SELECT rowid, distance
            FROM vec_rag_chunks
            WHERE embedding MATCH :qvec
            ORDER BY distance
            LIMIT {overfetch}
        )
        SELECT c.id, c.document_id, c.chunk_index, c.text, c.scope, knn.distance
        FROM knn
        JOIN rag_chunks c ON c.id = knn.rowid
        JOIN rag_documents d ON d.id = c.document_id
        WHERE (c.scope = :scope OR c.scope = 'GLOBAL')
          AND (:uploaded_by IS NULL OR d.uploaded_by = :uploaded_by)
        ORDER BY knn.distance
        LIMIT {top_k}
    """)

    with db_session() as db:
        rows = db.execute(
            sql, {"qvec": qjson, "scope": scope, "uploaded_by": uploaded_by}
        ).fetchall()

    results: list[dict] = []
    for r in rows:
        if max_distance is not None and r.distance > max_distance:
            continue
        results.append(
            {
                "chunk_id": r.id,
                "document_id": r.document_id,
                "chunk_index": r.chunk_index,
                "text": r.text,
                "scope": r.scope,
                "distance": r.distance,
            }
        )
    return results


# ============= GESTION DES DOCUMENTS =============


def list_documents(uploaded_by: str | None = None) -> list[dict]:
    """Liste les fiches documents (pour l'UI base de connaissances).

    `uploaded_by` (optionnel) : ne renvoie que les documents de cet utilisateur
    (base de connaissances privée). None = tous les documents.
    """
    with db_session() as db:
        q = db.query(RagDocument)
        if uploaded_by is not None:
            q = q.filter(RagDocument.uploaded_by == uploaded_by)
        docs = q.order_by(RagDocument.created_at.desc()).all()
        return [
            {
                "id": d.id,
                "title": d.title,
                "filename": d.filename,
                "scope": d.scope,
                "source_type": d.source_type,
                "status": d.status,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at,
            }
            for d in docs
        ]


def delete_document(doc_id: int, uploaded_by: str | None = None) -> int:
    """Supprime un document, ses chunks (cascade ORM) ET ses vecteurs vec0.

    `uploaded_by` (optionnel) : si fourni, la suppression n'a lieu QUE si le
    document appartient à cet utilisateur (base privée). Sinon on renvoie -1
    (interdit / introuvable pour cet utilisateur) sans rien supprimer.
    Renvoie le nombre de chunks supprimés (>=0), ou -1 si non autorisé/introuvable.
    La suppression des vecteurs est faite explicitement car la table vec0 n'est
    pas gérée par l'ORM.
    """
    with db_session() as db:
        doc = db.get(RagDocument, doc_id)
        if doc is None or (uploaded_by is not None and doc.uploaded_by != uploaded_by):
            return -1
        chunk_ids = [c.id for c in db.query(RagChunk).filter_by(document_id=doc_id).all()]
        for cid in chunk_ids:
            db.execute(text("DELETE FROM vec_rag_chunks WHERE rowid = :rid"), {"rid": cid})
        db.delete(doc)  # cascade ORM -> supprime les rag_chunks
        logger.info("RAG: document id=%s supprimé (%d chunks).", doc_id, len(chunk_ids))
        return len(chunk_ids)
