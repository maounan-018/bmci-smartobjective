#!/usr/bin/env python3
"""
controllers/ai_controller.py — Domaine "IA & Import Excel" (transversal).

RÔLE
    Routes d'analyse IA unitaire et d'import Excel intelligent, accessibles à
    plusieurs rôles. Toute la logique est déléguée à user_service / ai_service /
    excel_import_service.

EMPLACEMENT MVC
    Couche "controllers" : routes FastAPI.
"""

from datetime import datetime

from app.controllers.auth_controller import get_current_user
from app.controllers.dependencies import ai_rate_limited_user
from app.models.audit_log import AuditEventType
from app.schemas.analysis_schema import AlignmentRequest, SmartRequest
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services import audit_service, excel_import_service, permission_service
from app.services.ai_service import (
    analyze_alignment_internal,
    analyze_smart_internal,
    run_chat_coach,
)
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api", tags=["IA & Import"])


@router.post("/analyze-smart")
def analyze_smart(request: SmartRequest, current_user: dict = Depends(ai_rate_limited_user)):
    """Analyse SMART unitaire (authentifié, quota IA appliqué)."""
    return analyze_smart_internal(request.title, request.description)


@router.post("/analyze-alignment")
def analyze_alignment(
    request: AlignmentRequest, current_user: dict = Depends(ai_rate_limited_user)
):
    """Analyse d'alignement unitaire (authentifié, quota IA appliqué)."""
    return analyze_alignment_internal(request.objectiveTitle, request.companyObjectives)


@router.post("/import-excel-analyze")
async def import_excel_and_analyze(
    file: UploadFile = File(...),
    current_user: dict = Depends(ai_rate_limited_user),
):
    """Import Excel + analyse SMART/alignement en lot (résultats JSON)."""
    content = await file.read()
    return excel_import_service.run_import_analyze(content, file.filename, current_user)


@router.post("/import-excel-export")
async def import_excel_and_export(
    file: UploadFile = File(...),
    current_user: dict = Depends(ai_rate_limited_user),
):
    """Import Excel + analyse ; retourne un classeur Excel enrichi."""
    content = await file.read()
    result_excel = excel_import_service.run_import_export(content, file.filename, current_user)
    filename = f"analyse_smart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        result_excel,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/scan-excel")
async def scan_excel_structure(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Scanne la structure d'un fichier Excel (prévisualisation avant import)."""
    content = await file.read()
    return excel_import_service.run_scan(content, file.filename)


@router.post("/chat-coach", response_model=ChatResponse)
def chat_coach(request: ChatRequest, current_user: dict = Depends(ai_rate_limited_user)):
    """Conversation avec le Coach IA SMART (MANAGER/COLLAB/HR, quota IA).

    Le Coach guide pas à pas vers un objectif SMART et s'appuie sur la base de
    connaissances PRIVÉE de l'utilisateur (RAG) : il n'utilise que les documents
    que cet utilisateur a lui-même téléversés.
    """
    permission_service.require_role(current_user, ["MANAGER", "COLLAB", "HR"])
    response = run_chat_coach(request.messages, uploaded_by=current_user["id"])
    # Traçabilité (conformité) : on journalise chaque tour de Coach — qui, quand, et
    # l'objectif final produit le cas échéant — dans l'audit trail (no-throw, filtré).
    detail = "Coach IA — tour de conversation"
    if response.ready and response.final_objective:
        detail += f" (objectif final : {response.final_objective})"
    audit_service.log_event(
        AuditEventType.AI_REQUEST_SENT,
        description=detail,
        user_id=current_user.get("id"),
        username=current_user.get("username") or current_user.get("email"),
        role=current_user.get("role"),
        endpoint="/api/chat-coach",
        http_method="POST",
    )
    return response
