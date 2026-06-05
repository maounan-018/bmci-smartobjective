#!/usr/bin/env python3
"""
services/manager_service.py — Logique métier du domaine Manager (+ vue Collaborateur).

RÔLE
    Objectifs d'équipe (hors imports RH), statistiques, analyses privées Manager
    et Collaborateur, analyse SMART d'un objectif d'équipe ou personnel, et export
    Excel/PDF. ISOLATION STRICTE : aucune donnée Manager n'est visible côté RH.

EMPLACEMENT MVC
    Couche "services" : logique métier.
"""

import json
import secrets
from datetime import datetime

from fastapi import HTTPException

from app.database.session import db_session
from app.repositories import (
    user_repository,
    objective_repository,
    company_objective_repository,
    analysis_repository,
)
from app.services import objective_service
from app.services.ai_service import analyze_smart_internal, analyze_alignment_internal
from app.services.export_service import generate_manager_excel, generate_manager_pdf
from app.utils.helpers import safe_int


def _require_manager(current_user: dict) -> None:
    if current_user["role"] != "MANAGER":
        raise HTTPException(status_code=403, detail="Accès réservé aux managers.")


def _smart_flags_score(smart_result: dict) -> float:
    """Score SMART en pourcentage à partir des 5 booléens S/M/A/R/T."""
    return (
        (1 if smart_result.get("S") else 0)
        + (1 if smart_result.get("M") else 0)
        + (1 if smart_result.get("A") else 0)
        + (1 if smart_result.get("R") else 0)
        + (1 if smart_result.get("T") else 0)
    ) / 5 * 100


def _finalize_result(result: dict) -> dict:
    """Parse les analyses JSON et construit un titre/horodatage d'affichage."""
    for key in ("smart_analysis", "alignment_analysis"):
        if result.get(key):
            try:
                result[key] = json.loads(result[key])
            except (json.JSONDecodeError, TypeError):
                result[key] = None
    analyzed_date = (result.get("analyzed_at") or "")[:10]
    if result.get("objective_title"):
        title = result["objective_title"]
    elif result.get("top_issue"):
        title = f"Analyse du {analyzed_date}"
    else:
        title = f"Objectif analysé le {analyzed_date}"
    result["objective_title"] = title
    result["analyzed_at"] = result.get("analyzed_at") or datetime.now().isoformat()
    return result


def _smart_values(smart_result: dict) -> dict:
    """Sous-scores entiers + nombre d'issues + issue principale."""
    issues = smart_result.get("issues", [])
    return {
        "s_score": 1 if smart_result.get("S") else 0,
        "m_score": 1 if smart_result.get("M") else 0,
        "a_score": 1 if smart_result.get("A") else 0,
        "r_score": 1 if smart_result.get("R") else 0,
        "t_score": 1 if smart_result.get("T") else 0,
        "issues_count": len(issues),
        "top_issue": issues[0].get("problem", "") if issues else "",
    }


# ============= OBJECTIFS / ÉQUIPE =============

def get_objectives(current_user: dict) -> dict:
    """Objectifs de l'équipe (hors objectifs importés/analysés par le RH)."""
    _require_manager(current_user)
    with db_session() as db:
        team_ids = user_repository.get_team_ids(db, current_user["id"])
        if not team_ids:
            return {"objectives": [], "team_count": 0, "scope": "MANAGER"}
        rows = objective_repository.list_team_active(db, team_ids)
        objectives = []
        for o in rows:
            obj = o.to_dict()
            obj["user_name"] = o.user.name if o.user else None
            obj["user_email"] = o.user.email if o.user else None
            objective_service._parse_analyses(obj)
            objectives.append(obj)
        return {"objectives": objectives, "team_count": len(team_ids), "scope": "MANAGER"}


def get_team_stats(current_user: dict) -> dict:
    """Statistiques d'équipe pour le manager."""
    _require_manager(current_user)
    with db_session() as db:
        team_ids = user_repository.get_team_ids(db, current_user["id"])
    stats = objective_service.compute_team_stats(team_ids)
    stats["team_members"] = len(team_ids)
    stats["manager_id"] = current_user["id"]
    return stats


def get_team(current_user: dict) -> dict:
    """Membres de l'équipe du manager."""
    _require_manager(current_user)
    with db_session() as db:
        members = user_repository.get_team_members(db, current_user["id"])
        return {
            "members": [
                {"id": m.id, "name": m.name, "email": m.email, "created_at": m.created_at}
                for m in members
            ],
            "manager_id": current_user["id"],
        }


# ============= RÉSULTATS D'ANALYSE PRIVÉS =============

def get_analysis_results(current_user: dict) -> dict:
    """Résultats d'analyse Manager (table privée, invisible pour le RH)."""
    _require_manager(current_user)
    with db_session() as db:
        results = [_finalize_result(r) for r in analysis_repository.list_manager_results(db, current_user["id"])]
        stats = analysis_repository.manager_stats(db, current_user["id"])
    return {
        "results": results,
        "stats": {
            "total_analyzed": stats.get("total_analyzed", 0),
            "avg_smart_score": round(stats.get("avg_smart_score") or 0, 1),
            "avg_alignment_score": round(stats.get("avg_alignment_score") or 0, 1),
            "criteria_totals": {
                "S": stats.get("total_s", 0),
                "M": stats.get("total_m", 0),
                "A": stats.get("total_a", 0),
                "R": stats.get("total_r", 0),
                "T": stats.get("total_t", 0),
            },
            "total_issues": stats.get("total_issues", 0),
        },
        "scope": "MANAGER_PRIVATE",
        "manager_id": current_user["id"],
    }


def get_collab_analysis_results(current_user: dict) -> dict:
    """Résultats d'analyse Collaborateur (table privée collab_analysis_results)."""
    if current_user["role"] != "COLLAB":
        raise HTTPException(status_code=403, detail="Accès réservé aux collaborateurs.")
    with db_session() as db:
        results = [_finalize_result(r) for r in analysis_repository.list_collab_results(db, current_user["id"])]
        stats = analysis_repository.collab_stats(db, current_user["id"])
    return {
        "results": results,
        "stats": {
            "total_analyzed": stats.get("total_analyzed", 0),
            "avg_smart_score": round(stats.get("avg_smart_score") or 0, 1),
            "avg_alignment_score": round(stats.get("avg_alignment_score") or 0, 1),
            "criteria_totals": {
                "S": safe_int(stats.get("total_s", 0)),
                "M": safe_int(stats.get("total_m", 0)),
                "A": safe_int(stats.get("total_a", 0)),
                "R": safe_int(stats.get("total_r", 0)),
                "T": safe_int(stats.get("total_t", 0)),
            },
            "total_issues": safe_int(stats.get("total_issues", 0)),
        },
        "scope": "COLLAB_PRIVATE",
        "user_id": current_user["id"],
    }


# ============= ANALYSES IA =============

def analyze_personal(request, current_user: dict) -> dict:
    """Analyse SMART de l'objectif PERSONNEL du Manager (table privée)."""
    _require_manager(current_user)
    smart_result = analyze_smart_internal(request.title, request.description or "")

    with db_session() as db:
        company_objectives = company_objective_repository.list_for_alignment(db)

    if company_objectives:
        alignment_result = analyze_alignment_internal(request.title, company_objectives)
    else:
        alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": ["Aucun objectif stratégique défini"]}

    smart_score = _smart_flags_score(smart_result)
    sv = _smart_values(smart_result)
    result_id = f"mgr-personal-{secrets.token_hex(6)}"

    with db_session() as db:
        analysis_repository.insert_manager(db, {
            "id": result_id,
            "objective_id": f"personal-{result_id}",
            "manager_id": current_user["id"],
            "objective_title": request.title,
            "smart_analysis": json.dumps(smart_result),
            "alignment_analysis": json.dumps(alignment_result),
            "smart_score": smart_score,
            "alignment_score": alignment_result.get("alignment_score", 0),
            "analyzed_at": datetime.now().isoformat(),
            **sv,
        })

    return {
        "success": True,
        "result_id": result_id,
        "title": request.title,
        "description": request.description,
        "smart_analysis": smart_result,
        "alignment_analysis": alignment_result,
        "smart_score": smart_score,
        "scope": "MANAGER_PERSONAL",
    }


def analyze_objective(objective_id: str, current_user: dict) -> dict:
    """Analyse un objectif d'un collaborateur de l'équipe du manager."""
    _require_manager(current_user)

    with db_session() as db:
        o = objective_repository.get_with_user(db, objective_id)
        if not o:
            raise HTTPException(status_code=404, detail="Objectif non trouvé.")
        if not o.user or o.user.manager_id != current_user["id"]:
            raise HTTPException(status_code=403, detail="Cet objectif n'appartient pas à votre équipe.")
        title = o.title
        description = o.description or ""
        company_objectives = company_objective_repository.list_for_alignment(db)

    smart_result = analyze_smart_internal(title, description)
    if company_objectives:
        alignment_result = analyze_alignment_internal(title, company_objectives)
    else:
        alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": ["Aucun objectif stratégique défini"]}

    smart_score = _smart_flags_score(smart_result)
    sv = _smart_values(smart_result)

    with db_session() as db:
        objective_repository.update_fields(db, objective_id, {
            "smart_analysis": json.dumps(smart_result),
            "alignment_analysis": json.dumps(alignment_result),
            "analyzed_by_role": "MANAGER",
            "analyzed_by_user_id": current_user["id"],
            "data_scope": "MANAGER",
            "status": "analyzed",
            "updated_at": datetime.now().isoformat(),
        })
        analysis_repository.upsert_manager(db, {
            "id": f"mgr-res-{objective_id}",
            "objective_id": objective_id,
            "manager_id": current_user["id"],
            "objective_title": title,
            "smart_analysis": json.dumps(smart_result),
            "alignment_analysis": json.dumps(alignment_result),
            "smart_score": smart_score,
            "alignment_score": alignment_result.get("alignment_score", 0),
            "analyzed_at": datetime.now().isoformat(),
            **sv,
        })

    return {
        "success": True,
        "objective_id": objective_id,
        "smart_analysis": smart_result,
        "alignment_analysis": alignment_result,
        "scope": "MANAGER",
    }


# ============= EXPORT =============

def export_data(export_format: str, current_user: dict):
    """Export Excel (défaut) ou PDF des données d'équipe du Manager."""
    _require_manager(current_user)
    with db_session() as db:
        objectives = analysis_repository.manager_export_objectives(db, current_user["id"])
        personal_analyses = analysis_repository.manager_export_personal(db, current_user["id"])

    if (export_format or "").lower() == "pdf":
        return generate_manager_pdf(objectives, personal_analyses, current_user)
    return generate_manager_excel(objectives, personal_analyses, current_user)
