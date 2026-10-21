#!/usr/bin/env python3
"""
services/hr_analysis_service.py — Analyses & lecture du domaine RH.

RÔLE
    Analyse SMART personnelle RH, analyse en lot (SSE), tableaux de bord
    analytiques, liste détaillée et historique des imports. ISOLATION STRICTE :
    périmètre HR uniquement.

EMPLACEMENT MVC
    Couche "services" : logique métier RH (analyses & lecture).
"""

import json
import logging
import secrets
from datetime import datetime

from app.core.config import settings
from app.database.session import db_session
from app.repositories import (
    analysis_repository,
    company_objective_repository,
    hr_import_repository,
    objective_repository,
)
from app.services.ai_service import analyze_alignment_internal, analyze_smart_internal
from app.services.hr_common import require_hr
from app.utils.helpers import smart_flags_score, smart_values

logger = logging.getLogger(__name__)


# ============= ANALYSE PERSONNELLE RH =============


def analyze_personal(request, current_user: dict) -> dict:
    """Analyse SMART d'un objectif personnel RH, stockée dans hr_analysis_results."""
    require_hr(current_user)
    smart_result = analyze_smart_internal(request.title, request.description or "")

    with db_session() as db:
        company_objectives = company_objective_repository.list_for_alignment(db)

    if company_objectives:
        alignment_result = analyze_alignment_internal(request.title, company_objectives)
    else:
        alignment_result = {
            "alignment_score": 0,
            "top_matches": [],
            "gaps": ["Aucun objectif stratégique défini"],
        }

    smart_score = smart_flags_score(smart_result)
    sv = smart_values(smart_result)
    result_id = f"hr-personal-{secrets.token_hex(6)}"

    with db_session() as db:
        analysis_repository.insert_hr(
            db,
            {
                "id": result_id,
                "objective_id": f"hr-obj-{result_id}",
                "objective_title": request.title,
                "smart_analysis": json.dumps(smart_result),
                "alignment_analysis": json.dumps(alignment_result),
                "smart_score": smart_score,
                "alignment_score": alignment_result.get("alignment_score", 0),
                "analyzed_at": datetime.now().isoformat(),
                **sv,
            },
        )

    return {
        "success": True,
        "result_id": result_id,
        "title": request.title,
        "description": request.description,
        "smart_analysis": smart_result,
        "alignment_analysis": alignment_result,
        "smart_score": smart_score,
        "scope": "HR_PERSONAL",
    }


def get_analysis_results(current_user: dict) -> dict:
    """Résultats d'analyse personnels du RH."""
    require_hr(current_user)
    with db_session() as db:
        rows = analysis_repository.list_hr_personal_results(db)
        stats = analysis_repository.hr_personal_stats(db)

    results = []
    for result in rows:
        for key in ("smart_analysis", "alignment_analysis"):
            if result.get(key):
                try:
                    result[key] = json.loads(result[key])
                except (json.JSONDecodeError, TypeError):
                    result[key] = None
        if not result.get("objective_title"):
            result["objective_title"] = (
                result.get("obj_title") or f"Objectif {result.get('objective_id', 'N/A')}"
            )
        results.append(result)

    return {
        "results": results,
        "stats": {
            "total_analyzed": stats.get("total_analyzed", 0),
            "avg_smart_score": round(stats.get("avg_smart_score") or 0, 1),
            "avg_alignment_score": round(stats.get("avg_alignment_score") or 0, 1),
        },
        "scope": "HR_PERSONAL",
    }


# ============= ANALYSE EN LOT (SSE) =============


def build_batch_generator(objective_ids: list[str], current_user: dict, force: bool = False):
    """
    Prépare l'analyse en lot et retourne un générateur SSE (text/event-stream).
    Seuls les objectifs de périmètre HR sont analysés.

    - objective_ids fournis -> ces objectifs (ré-analyse ciblée).
    - sinon force=True       -> TOUS les objectifs HR (régénère les analyses existantes).
    - sinon                  -> seulement les NON analysés (idempotent, défaut).
    """
    require_hr(current_user)

    with db_session() as db:
        if objective_ids:
            objs = objective_repository.list_hr_by_ids(db, objective_ids)
        elif force:
            objs = objective_repository.list_hr_all(db, limit=500)
        else:
            objs = objective_repository.list_unanalyzed_hr(db, limit=100)
        objectives = [{"id": o.id, "title": o.title, "description": o.description} for o in objs]
        company_objectives = company_objective_repository.list_for_alignment(db)

    total = len(objectives)
    user_id = current_user["id"]

    def generate():
        results = []
        analyzed = 0
        errors = 0
        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

        for idx, obj in enumerate(objectives):
            yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'title': obj['title'][:80]})}\n\n"
            try:
                try:
                    smart_result = analyze_smart_internal(obj["title"], obj.get("description", ""))
                except Exception:
                    smart_result = {
                        "S": False,
                        "M": False,
                        "A": False,
                        "R": False,
                        "T": False,
                        "overall": False,
                        "confidence": 0,
                        "issues": [],
                    }

                if company_objectives:
                    try:
                        alignment_result = analyze_alignment_internal(
                            obj["title"], company_objectives
                        )
                    except Exception:
                        alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": []}
                else:
                    alignment_result = {
                        "alignment_score": 0,
                        "top_matches": [],
                        "gaps": ["Aucun objectif stratégique défini"],
                    }

                smart_score = smart_flags_score(smart_result)
                sv = smart_values(smart_result)

                with db_session() as db:
                    objective_repository.update_fields(
                        db,
                        obj["id"],
                        {
                            "smart_analysis": json.dumps(smart_result),
                            "alignment_analysis": json.dumps(alignment_result),
                            "analyzed_by_role": "HR",
                            "analyzed_by_user_id": user_id,
                            "data_scope": "HR",
                            "status": "analyzed",
                            "updated_at": datetime.now().isoformat(),
                        },
                    )
                    analysis_repository.upsert_hr(
                        db,
                        {
                            "id": f"res-{obj['id']}",
                            "objective_id": obj["id"],
                            "smart_score": smart_score,
                            "alignment_score": alignment_result.get("alignment_score", 0),
                            "issues_count": sv["issues_count"],
                            "top_issue": sv["top_issue"],
                            "analyzed_at": datetime.now().isoformat(),
                            "s_score": sv["s_score"],
                            "m_score": sv["m_score"],
                            "a_score": sv["a_score"],
                            "r_score": sv["r_score"],
                            "t_score": sv["t_score"],
                        },
                    )

                results.append(
                    {
                        "id": obj["id"],
                        "title": obj["title"],
                        "smart_score": smart_score,
                        "alignment_score": alignment_result.get("alignment_score", 0),
                        "success": True,
                    }
                )
                analyzed += 1
            except Exception as e:
                logger.error("Erreur analyse en lot pour %s: %s", obj["id"], e)
                results.append(
                    {"id": obj["id"], "title": obj["title"], "success": False, "error": str(e)}
                )
                errors += 1

        yield f"data: {json.dumps({'type': 'done', 'success': True, 'analyzed': analyzed, 'errors': errors, 'results': results})}\n\n"

    return generate


# ============= ANALYTICS / DÉTAILS / HISTORIQUE =============


def _compute_axis_coverage(axes: list, objective_rows: list, over_threshold: float) -> dict:
    """Couverture stratégique par axe (E4).

    Chaque objectif est rattaché à son axe PRINCIPAL (le top_match le mieux noté).
    On compte les objectifs par axe, on calcule la part (%), et on signale les axes
    ORPHELINS (0 objectif) et SUR-CONCENTRÉS (part > seuil).
    """
    counts = {str(a["id"]): 0 for a in axes}
    titles = {str(a["id"]): (a.get("title") or str(a["id"])) for a in axes}
    total_aligned = 0

    for o in objective_rows:
        raw = o.get("alignment_analysis")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = None
        if not isinstance(raw, dict):
            continue
        matches = [
            m
            for m in (raw.get("top_matches") or [])
            if isinstance(m, dict) and m.get("objective_id") is not None
        ]
        if not matches:
            continue
        primary = max(matches, key=lambda m: m.get("score") or 0)
        axis_id = str(primary.get("objective_id"))
        if axis_id in counts:
            counts[axis_id] += 1
            total_aligned += 1

    coverage = []
    for aid, cnt in counts.items():
        share = round(cnt / total_aligned * 100, 1) if total_aligned else 0.0
        coverage.append(
            {
                "axis_id": aid,
                "axis_title": titles.get(aid, aid),
                "count": cnt,
                "share_pct": share,
                "orphan": cnt == 0,
                "over_concentrated": share > over_threshold,
            }
        )
    coverage.sort(key=lambda x: x["count"], reverse=True)
    return {
        "axes": coverage,
        "total_aligned": total_aligned,
        "over_concentration_threshold": over_threshold,
    }


def _compute_low_confidence(objective_rows: list, threshold: float) -> dict:
    """Analyses à FAIBLE CONFIANCE IA (#2) — à relire par un humain.

    Compte les objectifs analysés dont le `confidence` du modèle (0.0-1.0) est
    sous le seuil : le modèle s'est lui-même déclaré incertain (ou a échoué =>
    confidence 0). L'IA est une aide à la décision : ces cas exigent une relecture.
    """
    count = 0
    for o in objective_rows:
        raw = o.get("smart_analysis")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = None
        if not isinstance(raw, dict):
            continue  # objectif non analysé -> hors périmètre relecture
        conf = raw.get("confidence")
        if isinstance(conf, int | float) and conf < threshold:
            count += 1
    return {"count": count, "threshold": threshold}


def get_analytics(current_user: dict, entity=None, manager=None, period=None) -> dict:
    """Tableaux de bord analytiques RH (KPI V1 inclus : taux + couverture par axe)."""
    require_hr(current_user)
    with db_session() as db:
        data = analysis_repository.hr_analytics(db, entity, manager, period)
        # Taux SMART conforme (E1) et alignement fort (E2) — seuils configurables.
        data["smart_rate"] = analysis_repository.hr_score_rate(
            db, "smart_score", settings.KPI_SMART_THRESHOLD, entity, manager, period
        )
        data["alignment_rate"] = analysis_repository.hr_score_rate(
            db, "alignment_score", settings.KPI_ALIGNMENT_STRONG, entity, manager, period
        )
        # Couverture stratégique par axe (E4) : axes + objectifs (avec alignement).
        axes = company_objective_repository.list_for_alignment(db)
        objective_rows = analysis_repository.hr_objectives_details(db, entity, manager, period)

    data["axis_coverage"] = _compute_axis_coverage(
        axes, objective_rows, settings.KPI_AXIS_OVERCONCENTRATION
    )

    # Faible confiance IA (#2) : analyses à relire par un humain.
    data["low_confidence"] = _compute_low_confidence(objective_rows, settings.KPI_AI_CONFIDENCE_MIN)

    # Volumétrie (E5) : sur quel volume reposent les chiffres.
    g = data.get("global_stats", {}) or {}
    total = g.get("total", 0) or 0
    analyzed = g.get("analyzed", 0) or 0
    data["volumetry"] = {
        "total": total,
        "analyzed": analyzed,
        "not_analyzed": max(0, total - analyzed),
    }

    # Seuils exposés au frontend (filtrage cohérent côté UI : « à ajuster » = < seuil SMART).
    data["thresholds"] = {
        "smart": settings.KPI_SMART_THRESHOLD,
        "alignment_strong": settings.KPI_ALIGNMENT_STRONG,
        "axis_over_concentration": settings.KPI_AXIS_OVERCONCENTRATION,
        "ai_confidence_min": settings.KPI_AI_CONFIDENCE_MIN,
    }

    return data


def get_objectives_details(
    current_user: dict,
    entity=None,
    manager=None,
    period=None,
    smart_filter=None,
    alignment_filter=None,
) -> dict:
    """Liste détaillée des objectifs RH avec filtres."""
    require_hr(current_user)
    with db_session() as db:
        rows = analysis_repository.hr_objectives_details(
            db, entity, manager, period, smart_filter, alignment_filter
        )
    for obj in rows:
        for key in ("smart_analysis", "alignment_analysis"):
            if obj.get(key):
                try:
                    obj[key] = json.loads(obj[key])
                except (json.JSONDecodeError, TypeError):
                    obj[key] = None
    return {"objectives": rows, "total": len(rows)}


def get_imports(current_user: dict) -> dict:
    """Historique des imports RH."""
    require_hr(current_user)
    with db_session() as db:
        return {"imports": [i.to_dict() for i in hr_import_repository.list_recent(db, limit=50)]}
