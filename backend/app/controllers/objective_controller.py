#!/usr/bin/env python3
"""
controllers/objective_controller.py — Domaine "objectifs".

RÔLE
    Routes des objectifs personnels, du catalogue stratégique d'entreprise et des
    vues d'équipe génériques. Toute la logique est déléguée à objective_service /
    user_service ; aucun accès base ici.

EMPLACEMENT MVC
    Couche "controllers" : routes FastAPI.
"""

from typing import List

from fastapi import APIRouter, Depends

from app.controllers.auth_controller import get_current_user
from app.schemas.objective_schema import (
    ObjectiveCreate, ObjectiveUpdate, CompanyObjectiveCreate,
)
from app.services import objective_service, user_service

router = APIRouter(prefix="/api", tags=["Objectifs"])


# ============= OBJECTIFS PERSONNELS =============

@router.get("/objectives")
def list_objectives(current_user: dict = Depends(get_current_user)):
    """Liste les objectifs accessibles selon le rôle."""
    return objective_service.list_objectives(current_user)


@router.post("/objectives")
def create_objective(request: ObjectiveCreate, current_user: dict = Depends(get_current_user)):
    """Crée un objectif (seulement pour soi-même)."""
    return objective_service.create_objective(current_user, request)


@router.get("/objectives/{objective_id}")
def get_objective(objective_id: str, current_user: dict = Depends(get_current_user)):
    """Récupère un objectif avec contrôle d'accès RBAC."""
    return objective_service.get_objective(objective_id, current_user)


@router.put("/objectives/{objective_id}")
def update_objective(objective_id: str, request: ObjectiveUpdate, current_user: dict = Depends(get_current_user)):
    """Met à jour un objectif (propriétaire ou HR uniquement)."""
    return objective_service.update_objective(objective_id, request, current_user)


@router.delete("/objectives/{objective_id}")
def delete_objective(objective_id: str, current_user: dict = Depends(get_current_user)):
    """Supprime un objectif (propriétaire ou HR uniquement)."""
    return objective_service.delete_objective(objective_id, current_user)


# ============= OBJECTIFS STRATÉGIQUES (CATALOGUE ENTREPRISE) =============

@router.get("/company-objectives")
def list_company_objectives():
    """Liste le catalogue stratégique (lecture publique)."""
    return objective_service.list_company_objectives()


@router.post("/company-objectives")
def create_company_objective(request: CompanyObjectiveCreate, current_user: dict = Depends(get_current_user)):
    """Crée un objectif stratégique (HR ou Manager seulement)."""
    return objective_service.create_company_objective(request, current_user)


@router.post("/company-objectives/batch")
def batch_create_company_objectives(objectives: List[CompanyObjectiveCreate], current_user: dict = Depends(get_current_user)):
    """Import batch d'objectifs stratégiques (HR ou Manager seulement)."""
    return objective_service.batch_create_company_objectives(objectives, current_user)


# ============= ÉQUIPE (générique, dépendant du rôle) =============

@router.get("/team/members")
def get_team_members(current_user: dict = Depends(get_current_user)):
    """Liste les membres de l'équipe — dépend du rôle (réservé MANAGER/HR)."""
    return user_service.get_team_members(current_user)


@router.get("/team/stats")
def get_team_stats(current_user: dict = Depends(get_current_user)):
    """Statistiques d'équipe génériques (MANAGER ; HR redirigé ; COLLAB refusé)."""
    return objective_service.get_team_stats_generic(current_user)
