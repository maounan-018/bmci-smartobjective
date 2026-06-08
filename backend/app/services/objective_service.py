#!/usr/bin/env python3
"""
services/objective_service.py — Logique métier des objectifs.

RÔLE
    Gère les objectifs personnels (CRUD filtré par rôle), le catalogue stratégique
    d'entreprise et les statistiques d'équipe génériques. Toute la persistance
    passe par les repositories ; le contrôle d'accès par le permission_service.

EMPLACEMENT MVC
    Couche "services" : logique métier.
"""

import json
import secrets
from datetime import datetime
from typing import List

from fastapi import HTTPException

from app.database.session import db_session
from app.repositories import objective_repository, company_objective_repository
from app.services import permission_service as perm

_EMPTY_DISTRIBUTION = {"not_started": 0, "in_progress": 0, "completed": 0, "on_hold": 0}


def _parse_analyses(obj: dict) -> dict:
    """Désérialise les analyses JSON (smart/alignment) stockées en TEXT."""
    for key in ("smart_analysis", "alignment_analysis"):
        if obj.get(key):
            try:
                obj[key] = json.loads(obj[key])
            except (json.JSONDecodeError, TypeError):
                obj[key] = None
    return obj


# ============= OBJECTIFS PERSONNELS =============

def list_objectives(current_user: dict) -> dict:
    """Liste les objectifs accessibles selon le rôle."""
    accessible_ids = perm.get_accessible_user_ids(current_user)
    if not accessible_ids:
        return {"objectives": []}

    with db_session() as db:
        rows = objective_repository.list_by_user_ids(db, accessible_ids)
        objectives = []
        for o in rows:
            obj = o.to_dict()
            obj["user_name"] = o.user.name if o.user else None
            obj["user_email"] = o.user.email if o.user else None
            objectives.append(_parse_analyses(obj))
        return {"objectives": objectives}


def create_objective(current_user: dict, request) -> dict:
    """Crée un objectif (uniquement pour soi-même)."""
    obj_id = f"obj-{secrets.token_hex(6)}"
    with db_session() as db:
        objective_repository.create(
            db,
            id=obj_id,
            user_id=current_user["id"],
            title=request.title,
            description=request.description,
            context=request.context,
        )
    return {
        "success": True,
        "objective": {
            "id": obj_id,
            "user_id": current_user["id"],
            "title": request.title,
            "description": request.description,
            "status": "draft",
            "progress": "not_started",
        },
    }


def get_objective(objective_id: str, current_user: dict) -> dict:
    """Récupère un objectif avec contrôle d'accès RBAC."""
    with db_session() as db:
        o = objective_repository.get_with_user(db, objective_id)
        if not o:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        obj = o.to_dict()
        obj["user_name"] = o.user.name if o.user else None

        if current_user["role"] == "COLLAB":
            perm.check_collab_access(current_user, obj["user_id"])
        elif current_user["role"] == "MANAGER":
            perm.check_manager_access(current_user, obj["user_id"])

        return {"objective": _parse_analyses(obj)}


def update_objective(objective_id: str, request, current_user: dict) -> dict:
    """Met à jour un objectif (propriétaire ou HR uniquement)."""
    with db_session() as db:
        o = objective_repository.get(db, objective_id)
        if not o:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        if current_user["role"] != "HR" and o.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres objectifs.")

        values: dict = {}
        if request.title is not None:
            values["title"] = request.title
        if request.description is not None:
            values["description"] = request.description
        if request.status is not None:
            values["status"] = request.status
        if request.progress is not None:
            values["progress"] = request.progress
        if request.smart_analysis is not None:
            values["smart_analysis"] = json.dumps(request.smart_analysis)
        if request.alignment_analysis is not None:
            values["alignment_analysis"] = json.dumps(request.alignment_analysis)

        if values:
            values["updated_at"] = datetime.now().isoformat()
            objective_repository.update_fields(db, objective_id, values)

    return {"success": True}


def delete_objective(objective_id: str, current_user: dict) -> dict:
    """Supprime un objectif (propriétaire ou HR uniquement)."""
    with db_session() as db:
        o = objective_repository.get(db, objective_id)
        if not o:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        if current_user["role"] != "HR" and o.user_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres objectifs.")
        objective_repository.delete_by_id(db, objective_id)
    return {"success": True}


# ============= OBJECTIFS STRATÉGIQUES (CATALOGUE ENTREPRISE) =============

def list_company_objectives() -> dict:
    """Liste le catalogue stratégique (lecture publique)."""
    with db_session() as db:
        return {"company_objectives": [c.to_dict() for c in company_objective_repository.list_all(db)]}


def create_company_objective(request, current_user: dict) -> dict:
    """Crée un objectif stratégique (HR ou Manager seulement)."""
    if current_user["role"] == "COLLAB":
        raise HTTPException(status_code=403, detail="Seuls les managers et RH peuvent créer des objectifs stratégiques.")

    obj_id = request.id or f"STRAT-{secrets.token_hex(4)}"
    with db_session() as db:
        company_objective_repository.create(
            db,
            id=obj_id,
            title=request.title,
            description=request.description,
            department=request.department,
            created_by=current_user["id"],
        )
    return {"success": True, "id": obj_id}


def batch_create_company_objectives(objectives: List, current_user: dict) -> dict:
    """Import batch d'objectifs stratégiques (HR ou Manager seulement)."""
    if current_user["role"] == "COLLAB":
        raise HTTPException(status_code=403, detail="Accès refusé.")

    created = 0
    with db_session() as db:
        for obj in objectives:
            obj_id = obj.id or f"STRAT-{secrets.token_hex(4)}"
            try:
                company_objective_repository.merge(db, {
                    "id": obj_id,
                    "title": obj.title,
                    "description": obj.description,
                    "department": obj.department,
                    "created_by": current_user["id"],
                })
                created += 1
            except Exception:
                pass
    return {"success": True, "created": created}


# ============= STATISTIQUES D'ÉQUIPE (génériques) =============

def compute_team_stats(team_ids: List[str]) -> dict:
    """
    Cœur de calcul des statistiques d'équipe (réutilisé par les domaines
    génériques et manager). Retourne total, taux SMART, alignement moyen et
    répartition d'avancement.
    """
    if not team_ids:
        return {
            "total_objectives": 0,
            "smart_rate": None,
            "avg_alignment": None,
            "progress_distribution": dict(_EMPTY_DISTRIBUTION),
        }

    with db_session() as db:
        total = objective_repository.count_by_user_ids(db, team_ids)
        if total == 0:
            return {
                "total_objectives": 0,
                "smart_rate": None,
                "avg_alignment": None,
                "progress_distribution": dict(_EMPTY_DISTRIBUTION),
            }

        smart_count = 0
        total_analyzed = 0
        for raw in objective_repository.get_smart_analyses(db, team_ids):
            try:
                analysis = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            total_analyzed += 1
            if analysis.get("overall"):
                smart_count += 1
        smart_rate = round((smart_count / total_analyzed) * 100) if total_analyzed > 0 else None

        alignment_scores = []
        for raw in objective_repository.get_alignment_analyses(db, team_ids):
            try:
                analysis = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if "alignment_score" in analysis:
                alignment_scores.append(analysis["alignment_score"])
        avg_alignment = round(sum(alignment_scores) / len(alignment_scores)) if alignment_scores else None

        progress_dist = dict(_EMPTY_DISTRIBUTION)
        for progress, count in objective_repository.get_progress_counts(db, team_ids):
            if progress in progress_dist:
                progress_dist[progress] = count

        return {
            "total_objectives": total,
            "smart_rate": smart_rate,
            "avg_alignment": avg_alignment,
            "progress_distribution": progress_dist,
        }


def get_team_stats_generic(current_user: dict) -> dict:
    """
    Statistiques d'équipe génériques (endpoint /api/team/stats) :
      - COLLAB  : accès refusé
      - HR      : redirigé vers /api/hr/analytics
      - MANAGER : stats de son équipe
    """
    if current_user["role"] == "COLLAB":
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")
    if current_user["role"] == "HR":
        raise HTTPException(
            status_code=400,
            detail="Les statistiques RH sont disponibles via /api/hr/analytics. Cet endpoint est réservé aux managers.",
        )

    team_ids = perm.get_manager_team_ids(current_user["id"])
    stats = compute_team_stats(team_ids)
    stats["team_members"] = len(team_ids)
    stats["scope"] = "manager_team"
    return stats
