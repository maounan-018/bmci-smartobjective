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

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.controllers.auth_controller import get_current_user
from app.controllers.dependencies import ai_rate_limited_user
from app.schemas.analysis_schema import SmartRequest, AlignmentRequest
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.ai_service import analyze_smart_internal, analyze_alignment_internal, run_chat_coach
from app.services import excel_import_service, permission_service

router = APIRouter(prefix="/api", tags=["IA & Import"])


@router.post("/analyze-smart")
def analyze_smart(request: SmartRequest, current_user: dict = Depends(ai_rate_limited_user)):
    """Analyse SMART unitaire (authentifié, quota IA appliqué)."""
    return analyze_smart_internal(request.title, request.description)


@router.post("/analyze-alignment")
def analyze_alignment(request: AlignmentRequest, current_user: dict = Depends(ai_rate_limited_user)):
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
    """Conversation avec le Coach IA SMART (réservé MANAGER/COLLAB, quota IA).

    Le Coach guide pas à pas vers un objectif SMART et s'appuie sur la base de
    connaissances (RAG) pour le contexte BMCI.
    """
    permission_service.require_role(current_user, ["MANAGER", "COLLAB"])
    return run_chat_coach(request.messages)