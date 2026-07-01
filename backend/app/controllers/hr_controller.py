#!/usr/bin/env python3
"""
controllers/hr_controller.py — Domaine "RH" (analytics, imports, exports).

RÔLE
    Routes réservées au rôle HR. Toute la logique (analyse, imports Excel,
    analytics, génération de documents) est déléguée à hr_service. Le controller
    se limite à lire les fichiers uploadés et à emballer les réponses streaming.

EMPLACEMENT MVC
    Couche "controllers" : routes FastAPI.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Body
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.controllers.auth_controller import get_current_user
from app.controllers.dependencies import ai_rate_limited_user
from app.schemas.hr_schema import HRPersonalAnalysisRequest
from app.services import hr_service

router = APIRouter(prefix="/api/hr", tags=["RH"])


@router.post("/analyze-personal")
def hr_analyze_personal_objective(
    request: HRPersonalAnalysisRequest,
    current_user: dict = Depends(ai_rate_limited_user),
):
    """Analyse SMART d'un objectif personnel RH (stocké en table privée, quota IA)."""
    return hr_service.analyze_personal(request, current_user)


@router.get("/analysis-results")
def get_hr_analysis_results(current_user: dict = Depends(get_current_user)):
    """Résultats d'analyse personnels du RH."""
    return hr_service.get_analysis_results(current_user)


@router.post("/import-strategy")
async def import_strategy_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Import Excel des objectifs stratégiques."""
    content = await file.read()
    # Travail bloquant (parsing + hachages PBKDF2 + DB) déporté dans un threadpool :
    # sinon la boucle asyncio est monopolisée et TOUT le serveur gèle pendant l'import.
    return await run_in_threadpool(hr_service.import_strategy, file.filename, content, current_user)


@router.post("/import-objectives")
async def import_objectives_excel(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Import Excel des objectifs collaborateurs (crée les comptes manquants)."""
    content = await file.read()
    # Travail bloquant (parsing + hachages PBKDF2 + DB) déporté dans un threadpool :
    # sinon la boucle asyncio est monopolisée et TOUT le serveur gèle pendant l'import.
    return await run_in_threadpool(hr_service.import_objectives, file.filename, content, current_user)


@router.post("/analyze-batch")
def analyze_batch(
    objective_ids: List[str] = Body(default=[]),
    force: bool = False,
    current_user: dict = Depends(ai_rate_limited_user),
):
    """Analyse batch d'objectifs RH (SMART + alignement) en streaming SSE (quota IA).

    `force=true` : ré-analyse TOUS les objectifs HR (régénère les analyses existantes)."""
    generator = hr_service.build_batch_generator(objective_ids, current_user, force=force)
    return StreamingResponse(generator(), media_type="text/event-stream")


@router.get("/analytics")
def get_hr_analytics(
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Analytics avancés pour le module RH."""
    return hr_service.get_analytics(current_user, entity_filter, manager_filter, period_filter)


@router.get("/objectives-details")
def get_hr_objectives_details(
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    smart_filter: Optional[str] = None,
    alignment_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Liste détaillée des objectifs RH avec filtres."""
    return hr_service.get_objectives_details(
        current_user, entity_filter, manager_filter, period_filter,
        smart_filter, alignment_filter,
    )


@router.get("/export-excel")
def export_hr_excel(
    export_type: str = "detailed",
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Export Excel des résultats RH (multi-feuilles)."""
    return hr_service.export_excel(current_user, entity_filter, manager_filter, period_filter)


@router.get("/export-pdf")
def export_hr_pdf(
    entity_filter: Optional[str] = None,
    manager_filter: Optional[str] = None,
    period_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Export PDF des résultats RH (synthèse + détail)."""
    return hr_service.export_pdf(current_user, entity_filter, manager_filter, period_filter)


@router.get("/imports")
def get_hr_imports(current_user: dict = Depends(get_current_user)):
    """Historique des imports RH."""
    return hr_service.get_imports(current_user)
