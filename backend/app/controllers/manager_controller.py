#!/usr/bin/env python3
"""
controllers/manager_controller.py — Domaine "manager" (+ analyses collaborateur).

RÔLE
    Routes réservées au rôle MANAGER et consultation des résultats privés du
    collaborateur. Toute la logique est déléguée à manager_service.

EMPLACEMENT MVC
    Couche "controllers" : routes FastAPI.
"""

from fastapi import APIRouter, Depends

from app.controllers.auth_controller import get_current_user
from app.schemas.analysis_schema import ManagerPersonalAnalysisRequest
from app.services import manager_service

router = APIRouter(prefix="/api", tags=["Manager"])


@router.get("/manager/objectives")
def get_manager_objectives(current_user: dict = Depends(get_current_user)):
    """Objectifs de l'équipe du manager (hors imports RH)."""
    return manager_service.get_objectives(current_user)


@router.get("/manager/team-stats")
def get_manager_team_stats(current_user: dict = Depends(get_current_user)):
    """Statistiques d'équipe pour le manager."""
    return manager_service.get_team_stats(current_user)


@router.get("/manager/team")
def get_manager_team(current_user: dict = Depends(get_current_user)):
    """Liste des membres de l'équipe du manager."""
    return manager_service.get_team(current_user)


@router.get("/manager/analysis-results")
def get_manager_analysis_results(current_user: dict = Depends(get_current_user)):
    """Résultats d'analyse du Manager (table privée, invisible pour le RH)."""
    return manager_service.get_analysis_results(current_user)


@router.get("/collab/analysis-results")
def get_collab_analysis_results(current_user: dict = Depends(get_current_user)):
    """Résultats d'analyse du Collaborateur (table privée)."""
    return manager_service.get_collab_analysis_results(current_user)


@router.post("/manager/analyze-personal")
def manager_analyze_personal_objective(
    request: ManagerPersonalAnalysisRequest,
    current_user: dict = Depends(get_current_user),
):
    """Analyse SMART de l'objectif personnel du Manager."""
    return manager_service.analyze_personal(request, current_user)


@router.post("/manager/analyze-objective/{objective_id}")
def manager_analyze_objective(objective_id: str, current_user: dict = Depends(get_current_user)):
    """Analyse un objectif d'un collaborateur de l'équipe."""
    return manager_service.analyze_objective(objective_id, current_user)


@router.get("/manager/export")
def export_manager_data(format: str = "excel", current_user: dict = Depends(get_current_user)):
    """Export des données d'équipe du Manager en Excel ou PDF."""
    return manager_service.export_data(format, current_user)
