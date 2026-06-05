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

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse

from app.controllers.auth_controller import get_current_user
from app.schemas.analysis_schema import SmartRequest, AlignmentRequest
from app.services import user_service
from app.services.ai_service import analyze_smart_internal, analyze_alignment_internal
from app.services import excel_import_service

router = APIRouter(prefix="/api", tags=["IA & Import"])


@router.get("/managers")
def list_managers():
    """Liste publique des managers pour la sélection à l'inscription (id/name/team)."""
    return {"managers": user_service.get_managers_public()}


@router.post("/analyze-smart")
def analyze_smart(request: SmartRequest, current_user: dict = Depends(get_current_user)):
    """Analyse SMART unitaire (authentifié)."""
    return analyze_smart_internal(request.title, request.description)


@router.post("/analyze-alignment")
def analyze_alignment(request: AlignmentRequest, current_user: dict = Depends(get_current_user)):
    """Analyse d'alignement unitaire (authentifié)."""
    return analyze_alignment_internal(request.objectiveTitle, request.companyObjectives)


@router.post("/import-excel-analyze")
async def import_excel_and_analyze(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Import Excel + analyse SMART/alignement en lot (résultats JSON)."""
    content = await file.read()
    return excel_import_service.run_import_analyze(content, file.filename, current_user)


@router.post("/import-excel-export")
async def import_excel_and_export(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
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