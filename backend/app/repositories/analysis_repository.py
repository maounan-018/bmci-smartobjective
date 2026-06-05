#!/usr/bin/env python3
"""
repositories/analysis_repository.py — Accès aux données des résultats d'analyse.

RÔLE
    Encapsule TOUT l'accès aux trois tables d'analyse (hr/manager/collab) ainsi
    que les requêtes analytiques RH (tableaux de bord, exports). Les écritures
    passent par l'ORM ; les lectures de reporting (jointures + COALESCE + agrégats
    + fenêtrage temporel) sont exprimées via `text()` — toujours au sein du
    repository, jamais dans les services/controllers — pour rester fidèles au
    comportement SQLite d'origine.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.analysis_result import (
    HRAnalysisResult,
    ManagerAnalysisResult,
    CollabAnalysisResult,
)


# ============================================================================
# ÉCRITURES (ORM)
# ============================================================================

def insert_hr(db: Session, values: dict) -> HRAnalysisResult:
    """Insère un résultat d'analyse RH."""
    row = HRAnalysisResult(**values)
    db.add(row)
    return row


def upsert_hr(db: Session, values: dict) -> HRAnalysisResult:
    """Upsert (INSERT OR REPLACE) d'un résultat d'analyse RH par clé primaire."""
    row = db.merge(HRAnalysisResult(**values))
    return row


def insert_manager(db: Session, values: dict) -> ManagerAnalysisResult:
    """Insère un résultat d'analyse Manager."""
    row = ManagerAnalysisResult(**values)
    db.add(row)
    return row


def upsert_manager(db: Session, values: dict) -> ManagerAnalysisResult:
    """Upsert d'un résultat d'analyse Manager."""
    row = db.merge(ManagerAnalysisResult(**values))
    return row


def insert_collab(db: Session, values: dict) -> CollabAnalysisResult:
    """Insère un résultat d'analyse Collaborateur."""
    row = CollabAnalysisResult(**values)
    db.add(row)
    return row


# ============================================================================
# LECTURES — Manager (table privée)
# ============================================================================

_MANAGER_RESULTS_SQL = text(
    """
    SELECT mar.id, mar.objective_id, mar.manager_id, mar.smart_score, mar.alignment_score,
           mar.s_score, mar.m_score, mar.a_score, mar.r_score, mar.t_score,
           mar.issues_count, mar.top_issue, mar.analyzed_at,
           COALESCE(mar.objective_title, o.title)                 AS objective_title,
           o.description                                          AS objective_description,
           COALESCE(mar.smart_analysis, o.smart_analysis)         AS smart_analysis,
           COALESCE(mar.alignment_analysis, o.alignment_analysis) AS alignment_analysis,
           u.name  AS collaborator_name,
           u.email AS collaborator_email
    FROM manager_analysis_results mar
    LEFT JOIN objectives o ON mar.objective_id = o.id
    LEFT JOIN users u ON o.user_id = u.id
    WHERE mar.manager_id = :manager_id
    ORDER BY mar.analyzed_at DESC
    """
)

_MANAGER_STATS_SQL = text(
    """
    SELECT COUNT(*) AS total_analyzed,
           AVG(smart_score) AS avg_smart_score,
           AVG(alignment_score) AS avg_alignment_score,
           SUM(s_score) AS total_s, SUM(m_score) AS total_m, SUM(a_score) AS total_a,
           SUM(r_score) AS total_r, SUM(t_score) AS total_t,
           SUM(issues_count) AS total_issues
    FROM manager_analysis_results
    WHERE manager_id = :manager_id
    """
)


def list_manager_results(db: Session, manager_id: str) -> List[dict]:
    """Résultats d'analyse Manager enrichis (titres/analyses via COALESCE)."""
    return [dict(r) for r in db.execute(_MANAGER_RESULTS_SQL, {"manager_id": manager_id}).mappings().all()]


def manager_stats(db: Session, manager_id: str) -> dict:
    """Statistiques agrégées des analyses Manager."""
    row = db.execute(_MANAGER_STATS_SQL, {"manager_id": manager_id}).mappings().first()
    return dict(row) if row else {}


# ============================================================================
# LECTURES — Collaborateur (table privée)
# ============================================================================

_COLLAB_RESULTS_SQL = text(
    """
    SELECT car.id, car.objective_id, car.user_id, car.smart_score, car.alignment_score,
           car.s_score, car.m_score, car.a_score, car.r_score, car.t_score,
           car.issues_count, car.top_issue, car.rewrite_fr, car.rewrite_en, car.analyzed_at,
           COALESCE(car.objective_title, o.title)                 AS objective_title,
           COALESCE(car.objective_description, o.description)     AS objective_description,
           COALESCE(car.smart_analysis, o.smart_analysis)         AS smart_analysis,
           COALESCE(car.alignment_analysis, o.alignment_analysis) AS alignment_analysis
    FROM collab_analysis_results car
    LEFT JOIN objectives o ON car.objective_id = o.id
    WHERE car.user_id = :user_id
    ORDER BY car.analyzed_at DESC
    """
)

_COLLAB_STATS_SQL = text(
    """
    SELECT COUNT(*) AS total_analyzed,
           AVG(smart_score) AS avg_smart_score,
           AVG(alignment_score) AS avg_alignment_score,
           SUM(s_score) AS total_s, SUM(m_score) AS total_m, SUM(a_score) AS total_a,
           SUM(r_score) AS total_r, SUM(t_score) AS total_t,
           SUM(issues_count) AS total_issues
    FROM collab_analysis_results
    WHERE user_id = :user_id
    """
)


def list_collab_results(db: Session, user_id: str) -> List[dict]:
    """Résultats d'analyse Collaborateur enrichis."""
    return [dict(r) for r in db.execute(_COLLAB_RESULTS_SQL, {"user_id": user_id}).mappings().all()]


def collab_stats(db: Session, user_id: str) -> dict:
    """Statistiques agrégées des analyses Collaborateur."""
    row = db.execute(_COLLAB_STATS_SQL, {"user_id": user_id}).mappings().first()
    return dict(row) if row else {}


# ============================================================================
# LECTURES — RH personnel
# ============================================================================

_HR_PERSONAL_RESULTS_SQL = text(
    """
    SELECT har.*, o.title AS obj_title, o.description AS obj_description
    FROM hr_analysis_results har
    LEFT JOIN objectives o ON har.objective_id = o.id
    WHERE LOWER(har.objective_id) LIKE 'hr-obj-%' OR LOWER(har.objective_id) LIKE 'hr_obj_%'
    ORDER BY har.analyzed_at DESC
    """
)

_HR_PERSONAL_STATS_SQL = text(
    """
    SELECT COUNT(*) AS total_analyzed,
           AVG(smart_score) AS avg_smart_score,
           AVG(alignment_score) AS avg_alignment_score
    FROM hr_analysis_results
    WHERE LOWER(objective_id) LIKE 'hr-obj-%' OR LOWER(objective_id) LIKE 'hr_obj_%'
    """
)


def list_hr_personal_results(db: Session) -> List[dict]:
    """Analyses personnelles RH (objectifs saisis par un membre RH)."""
    return [dict(r) for r in db.execute(_HR_PERSONAL_RESULTS_SQL).mappings().all()]


def hr_personal_stats(db: Session) -> dict:
    """Statistiques des analyses personnelles RH."""
    row = db.execute(_HR_PERSONAL_STATS_SQL).mappings().first()
    return dict(row) if row else {}


# ============================================================================
# ANALYTICS RH (tableaux de bord) — données HR uniquement
# ============================================================================

def _hr_filters(entity: Optional[str], manager: Optional[str], period: Optional[str]) -> Tuple[str, dict]:
    """
    Construit la clause WHERE (sans le mot-clé WHERE) restreinte aux données RH,
    avec filtres optionnels, et les paramètres nommés associés.
    """
    clauses = ["(o.data_scope = 'HR' OR o.import_batch_id LIKE 'obj-%')"]
    params: dict = {}
    if entity:
        clauses.append("o.entity LIKE :entity")
        params["entity"] = f"%{entity}%"
    if manager:
        clauses.append("o.manager_name LIKE :manager")
        params["manager"] = f"%{manager}%"
    if period:
        clauses.append("o.period LIKE :period")
        params["period"] = f"%{period}%"
    return " AND ".join(clauses), params


def hr_analytics(
    db: Session,
    entity: Optional[str] = None,
    manager: Optional[str] = None,
    period: Optional[str] = None,
) -> dict:
    """Agrège l'ensemble des indicateurs du tableau de bord RH."""
    where, p = _hr_filters(entity, manager, period)

    global_stats = dict(db.execute(text(f"""
        SELECT COUNT(*) AS total,
               COUNT(CASE WHEN smart_analysis IS NOT NULL THEN 1 END) AS analyzed,
               COUNT(CASE WHEN status = 'validated' THEN 1 END) AS validated
        FROM objectives o WHERE {where}
    """), p).mappings().first() or {})

    avg_scores = dict(db.execute(text(f"""
        SELECT AVG(r.smart_score) AS avg_smart, AVG(r.alignment_score) AS avg_alignment,
               AVG(r.s_score) AS avg_s, AVG(r.m_score) AS avg_m, AVG(r.a_score) AS avg_a,
               AVG(r.r_score) AS avg_r, AVG(r.t_score) AS avg_t
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where}
    """), p).mappings().first() or {})

    smart_evolution = [dict(r) for r in db.execute(text(f"""
        SELECT strftime('%Y-%m', r.analyzed_at) AS month, AVG(r.smart_score) AS avg_smart, COUNT(*) AS count
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where} GROUP BY strftime('%Y-%m', r.analyzed_at) ORDER BY month
    """), p).mappings().all()]

    alignment_evolution = [dict(r) for r in db.execute(text(f"""
        SELECT strftime('%Y-%m', r.analyzed_at) AS month, AVG(r.alignment_score) AS avg_alignment, COUNT(*) AS count
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where} GROUP BY strftime('%Y-%m', r.analyzed_at) ORDER BY month
    """), p).mappings().all()]

    smart_distribution = [dict(r) for r in db.execute(text(f"""
        SELECT CASE
                 WHEN r.smart_score >= 80 THEN 'Excellent (80-100%)'
                 WHEN r.smart_score >= 60 THEN 'Bon (60-79%)'
                 WHEN r.smart_score >= 40 THEN 'Moyen (40-59%)'
                 ELSE 'À améliorer (<40%)'
               END AS level, COUNT(*) AS count
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where} GROUP BY level
        ORDER BY CASE level
                 WHEN 'Excellent (80-100%)' THEN 1 WHEN 'Bon (60-79%)' THEN 2
                 WHEN 'Moyen (40-59%)' THEN 3 ELSE 4 END
    """), p).mappings().all()]

    alignment_distribution = [dict(r) for r in db.execute(text(f"""
        SELECT CASE
                 WHEN r.alignment_score >= 80 THEN 'Fort (80-100%)'
                 WHEN r.alignment_score >= 50 THEN 'Moyen (50-79%)'
                 ELSE 'Faible (<50%)'
               END AS level, COUNT(*) AS count
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where} GROUP BY level
    """), p).mappings().all()]

    blocking_points = [dict(r) for r in db.execute(text(f"""
        SELECT 'S - Spécifique' AS criteria, SUM(1 - r.s_score) AS failures
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id WHERE {where}
        UNION ALL
        SELECT 'M - Mesurable', SUM(1 - r.m_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id WHERE {where}
        UNION ALL
        SELECT 'A - Atteignable', SUM(1 - r.a_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id WHERE {where}
        UNION ALL
        SELECT 'R - Réaliste', SUM(1 - r.r_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id WHERE {where}
        UNION ALL
        SELECT 'T - Temporel', SUM(1 - r.t_score) FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id WHERE {where}
        ORDER BY failures DESC
    """), p).mappings().all()]

    entity_comparison = [dict(r) for r in db.execute(text(f"""
        SELECT COALESCE(NULLIF(o.entity, ''), 'Non spécifié') AS entity,
               AVG(r.smart_score) AS avg_smart, AVG(r.alignment_score) AS avg_alignment, COUNT(*) AS count
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where} GROUP BY entity ORDER BY avg_smart DESC
    """), p).mappings().all()]

    manager_comparison = [dict(r) for r in db.execute(text(f"""
        SELECT COALESCE(NULLIF(o.manager_name, ''), 'Non spécifié') AS manager,
               AVG(r.smart_score) AS avg_smart, AVG(r.alignment_score) AS avg_alignment, COUNT(*) AS count
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where} GROUP BY manager ORDER BY avg_smart DESC
    """), p).mappings().all()]

    period_comparison = [dict(r) for r in db.execute(text(f"""
        SELECT COALESCE(NULLIF(o.period, ''), 'Non spécifié') AS period,
               AVG(r.smart_score) AS avg_smart, AVG(r.alignment_score) AS avg_alignment, COUNT(*) AS count
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where} GROUP BY period ORDER BY period
    """), p).mappings().all()]

    return {
        "global_stats": global_stats,
        "avg_scores": avg_scores,
        "smart_evolution": smart_evolution,
        "alignment_evolution": alignment_evolution,
        "smart_distribution": smart_distribution,
        "alignment_distribution": alignment_distribution,
        "blocking_points": blocking_points,
        "entity_comparison": entity_comparison,
        "manager_comparison": manager_comparison,
        "period_comparison": period_comparison,
        "filters": {
            "entities": distinct_values(db, "entity"),
            "managers": distinct_values(db, "manager_name"),
            "periods": distinct_values(db, "period"),
        },
    }


def distinct_values(db: Session, column: str) -> List[str]:
    """Valeurs distinctes non vides d'une colonne d'objectifs (filtres UI)."""
    if column not in {"entity", "manager_name", "period"}:
        raise ValueError(f"Colonne non autorisée: {column}")
    sql = text(
        f"SELECT DISTINCT {column} FROM objectives "
        f"WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
    )
    return [r[0] for r in db.execute(sql).all()]


# ============================================================================
# LISTE DÉTAILLÉE + EXPORTS RH
# ============================================================================

def hr_objectives_details(
    db: Session,
    entity: Optional[str] = None,
    manager: Optional[str] = None,
    period: Optional[str] = None,
    smart_filter: Optional[str] = None,
    alignment_filter: Optional[str] = None,
) -> List[dict]:
    """Liste détaillée des objectifs RH avec filtres SMART/alignement."""
    where, p = _hr_filters(entity, manager, period)
    if smart_filter == "smart":
        where += " AND r.smart_score >= 80"
    elif smart_filter == "partial":
        where += " AND r.smart_score >= 40 AND r.smart_score < 80"
    elif smart_filter == "non-smart":
        where += " AND r.smart_score < 40"
    if alignment_filter == "high":
        where += " AND r.alignment_score >= 80"
    elif alignment_filter == "medium":
        where += " AND r.alignment_score >= 50 AND r.alignment_score < 80"
    elif alignment_filter == "low":
        where += " AND r.alignment_score < 50"

    sql = text(f"""
        SELECT o.id, o.title, o.description, o.entity, o.manager_name, o.period,
               u.name AS user_name, u.email AS user_email,
               o.smart_analysis, o.alignment_analysis,
               r.smart_score, r.alignment_score,
               r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
               r.issues_count, r.top_issue, o.created_at
        FROM objectives o
        LEFT JOIN users u ON o.user_id = u.id
        LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
        WHERE {where}
        ORDER BY o.created_at DESC
    """)
    return [dict(r) for r in db.execute(sql, p).mappings().all()]


def hr_export_detailed(db: Session, entity=None, manager=None, period=None) -> List[tuple]:
    """Lignes détaillées pour l'export Excel RH (ordre de colonnes figé)."""
    where, p = _hr_filters(entity, manager, period)
    sql = text(f"""
        SELECT o.id, u.name, u.email, o.entity, o.manager_name, o.period,
               o.title, o.description,
               r.smart_score, r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
               r.alignment_score, r.issues_count, r.top_issue, o.created_at
        FROM objectives o
        LEFT JOIN users u ON o.user_id = u.id
        LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
        WHERE {where}
        ORDER BY o.created_at DESC
    """)
    return [tuple(r) for r in db.execute(sql, p).all()]


def hr_export_entity_stats(db: Session, entity=None, manager=None, period=None) -> List[tuple]:
    """Stats par entité pour l'export Excel."""
    where, p = _hr_filters(entity, manager, period)
    sql = text(f"""
        SELECT COALESCE(NULLIF(o.entity, ''), 'Non spécifié') AS entity,
               COUNT(*) AS count, AVG(r.smart_score) AS avg_smart, AVG(r.alignment_score) AS avg_alignment
        FROM objectives o
        LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
        WHERE {where} GROUP BY entity ORDER BY avg_smart DESC
    """)
    return [tuple(r) for r in db.execute(sql, p).all()]


def hr_export_manager_stats(db: Session, entity=None, manager=None, period=None) -> List[tuple]:
    """Stats par manager pour l'export Excel."""
    where, p = _hr_filters(entity, manager, period)
    sql = text(f"""
        SELECT COALESCE(NULLIF(o.manager_name, ''), 'Non spécifié') AS manager,
               COUNT(*) AS count, AVG(r.smart_score) AS avg_smart, AVG(r.alignment_score) AS avg_alignment
        FROM objectives o
        LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
        WHERE {where} GROUP BY manager ORDER BY avg_smart DESC
    """)
    return [tuple(r) for r in db.execute(sql, p).all()]


def hr_count_objectives(db: Session, entity=None, manager=None, period=None) -> int:
    """Nombre d'objectifs dans le périmètre RH filtré."""
    where, p = _hr_filters(entity, manager, period)
    return int(db.execute(text(f"SELECT COUNT(*) FROM objectives o WHERE {where}"), p).scalar() or 0)


def hr_criteria_failures(db: Session, col_name: str, entity=None, manager=None, period=None) -> int:
    """Nombre de défaillances pour un critère SMART donné (s/m/a/r/t)."""
    if col_name not in {"s_score", "m_score", "a_score", "r_score", "t_score"}:
        raise ValueError(f"Critère non autorisé: {col_name}")
    where, p = _hr_filters(entity, manager, period)
    sql = text(f"""
        SELECT SUM(1 - r.{col_name})
        FROM hr_analysis_results r JOIN objectives o ON r.objective_id = o.id
        WHERE {where}
    """)
    return int(db.execute(sql, p).scalar() or 0)


def hr_export_pdf_rows(db: Session, entity=None, manager=None, period=None) -> List[dict]:
    """Objectifs (limités) pour le rapport PDF RH."""
    where, p = _hr_filters(entity, manager, period)
    sql = text(f"""
        SELECT o.id, u.name AS user_name, o.entity, o.manager_name, o.title,
               r.smart_score, r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
               r.alignment_score
        FROM objectives o
        LEFT JOIN users u ON o.user_id = u.id
        LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
        WHERE {where}
        ORDER BY o.entity, u.name
        LIMIT 100
    """)
    return [dict(r) for r in db.execute(sql, p).mappings().all()]


def hr_pdf_smart_count(db: Session, entity=None, manager=None, period=None) -> int:
    """Objectifs SMART (score >= 80) dans le périmètre RH filtré."""
    where, p = _hr_filters(entity, manager, period)
    sql = text(f"""
        SELECT COUNT(*) FROM objectives o
        LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
        WHERE {where} AND r.smart_score >= 80
    """)
    return int(db.execute(sql, p).scalar() or 0)


def hr_pdf_avg_alignment(db: Session, entity=None, manager=None, period=None) -> float:
    """Alignement moyen dans le périmètre RH filtré."""
    where, p = _hr_filters(entity, manager, period)
    sql = text(f"""
        SELECT AVG(r.alignment_score) FROM objectives o
        LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
        WHERE {where}
    """)
    return float(db.execute(sql, p).scalar() or 0)


# ============================================================================
# EXPORTS MANAGER
# ============================================================================

_MANAGER_EXPORT_OBJECTIVES_SQL = text(
    """
    SELECT o.id, u.name AS user_name, u.email, o.title, o.description, o.progress, o.created_at,
           r.smart_score, r.s_score, r.m_score, r.a_score, r.r_score, r.t_score,
           r.alignment_score, r.issues_count, r.top_issue
    FROM objectives o
    JOIN users u ON o.user_id = u.id
    LEFT JOIN hr_analysis_results r ON o.id = r.objective_id
    WHERE u.manager_id = :manager_id
    ORDER BY u.name, o.created_at DESC
    """
)

_MANAGER_EXPORT_PERSONAL_SQL = text(
    """
    SELECT id, objective_id, smart_score, s_score, m_score, a_score, r_score, t_score,
           alignment_score, issues_count, top_issue, analyzed_at, objective_title
    FROM manager_analysis_results
    WHERE manager_id = :manager_id
    ORDER BY analyzed_at DESC
    """
)


def manager_export_objectives(db: Session, manager_id: str) -> List[dict]:
    """Objectifs d'équipe (avec scores) pour l'export Manager."""
    return [dict(r) for r in db.execute(_MANAGER_EXPORT_OBJECTIVES_SQL, {"manager_id": manager_id}).mappings().all()]


def manager_export_personal(db: Session, manager_id: str) -> List[dict]:
    """Analyses personnelles du Manager pour l'export."""
    return [dict(r) for r in db.execute(_MANAGER_EXPORT_PERSONAL_SQL, {"manager_id": manager_id}).mappings().all()]
