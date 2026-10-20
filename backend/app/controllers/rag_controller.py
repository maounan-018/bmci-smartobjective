#!/usr/bin/env python3
"""
controllers/rag_controller.py — Base de connaissances de l'assistant (RAG).

RÔLE
    Gestion des documents qui alimentent la recherche sémantique de l'assistant :
    téléversement (extraction -> découpe -> embeddings), liste, suppression.
    Réservé aux rôles MANAGER et ADMIN : la base de connaissances de l'assistant
    est gérée côté manager.

EMPLACEMENT MVC
    Couche "controllers" : routes FastAPI ; logique déléguée à
    document_extractor + rag_service.
"""

import logging

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException

from app.controllers.auth_controller import get_current_user
from app.services import permission_service, rag_service, document_extractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["Base de connaissances"])

# Base de connaissances de l'assistant : accessible à tous les rôles métier
# (MANAGER, HR, COLLAB) + ADMIN. La base est partagée (scope GLOBAL) : tout
# utilisateur autorisé peut consulter, téléverser et supprimer des documents.
_ALLOWED_ROLES = ["MANAGER", "HR", "COLLAB", "ADMIN"]


@router.get("/documents")
def list_rag_documents(current_user: dict = Depends(get_current_user)):
    """Liste les documents de la base de connaissances (MANAGER/ADMIN)."""
    permission_service.require_role(current_user, _ALLOWED_ROLES)
    return rag_service.list_documents()


@router.post("/documents")
async def upload_rag_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    scope: str = Form("GLOBAL"),
    current_user: dict = Depends(get_current_user),
):
    """Téléverse un document et l'indexe (extraction -> chunks -> embeddings).

    Formats acceptés : PDF, Word (.docx), Excel (.xlsx), texte (.txt/.md).
    """
    permission_service.require_role(current_user, _ALLOWED_ROLES)

    content = await file.read()
    try:
        text = document_extractor.extract_text(file.filename, content)
    except ValueError as e:
        # Format non supporté ou fichier illisible -> erreur client (400).
        raise HTTPException(status_code=400, detail=str(e))

    source_type = document_extractor.file_extension(file.filename).lstrip(".") or "manual"
    try:
        return rag_service.ingest_document(
            text,
            filename=file.filename,
            title=(title or None),
            scope=(scope or "GLOBAL"),
            source_type=source_type,
            uploaded_by=current_user["id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/documents/{doc_id}")
def delete_rag_document(doc_id: int, current_user: dict = Depends(get_current_user)):
    """Supprime un document et ses vecteurs (MANAGER/ADMIN)."""
    permission_service.require_role(current_user, _ALLOWED_ROLES)
    removed = rag_service.delete_document(doc_id)
    return {"deleted": True, "document_id": doc_id, "chunks_removed": removed}
