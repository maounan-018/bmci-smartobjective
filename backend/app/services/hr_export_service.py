#!/usr/bin/env python3
"""
services/hr_export_service.py — Exports Excel/PDF du domaine RH.

RÔLE
    Construit les rapports RH (Excel multi-feuilles, PDF synthétique) à partir des
    agrégats du repository, puis délègue la génération du document à export_service.

EMPLACEMENT MVC
    Couche "services" : logique métier RH (exports).
"""

from app.database.session import db_session
from app.repositories import analysis_repository
from app.services import export_service
from app.services.hr_common import require_hr

_CRITERIA = [
    ("S - Spécifique", "s_score"),
    ("M - Mesurable", "m_score"),
    ("A - Atteignable", "a_score"),
    ("R - Réaliste", "r_score"),
    ("T - Temporel", "t_score"),
]


def export_excel(current_user: dict, entity=None, manager=None, period=None):
    """Construit le rapport Excel multi-feuilles RH."""
    require_hr(current_user)
    with db_session() as db:
        detailed = analysis_repository.hr_export_detailed(db, entity, manager, period)
        entity_stats = analysis_repository.hr_export_entity_stats(db, entity, manager, period)
        manager_stats = analysis_repository.hr_export_manager_stats(db, entity, manager, period)
        total_obj = analysis_repository.hr_count_objectives(db, entity, manager, period) or 1
        failures = [
            (label, analysis_repository.hr_criteria_failures(db, col, entity, manager, period))
            for label, col in _CRITERIA
        ]
    return export_service.generate_hr_excel(
        detailed, entity_stats, manager_stats, total_obj, failures
    )


def export_pdf(current_user: dict, entity=None, manager=None, period=None):
    """Construit le rapport PDF Direction / COMEX (KPI GLOBAUX, front-loaded).

    Réutilise les agrégats déjà calculés pour le tableau de bord RH
    (hr_analysis_service.get_analytics : taux SMART, par critère, couverture par
    axe, distributions...) et les restitue via comex_report_service.
    """
    require_hr(current_user)
    # Import local : évite tout souci d'ordre d'import entre services.
    from app.services import comex_report_service, hr_analysis_service

    analytics = hr_analysis_service.get_analytics(current_user, entity, manager, period)
    # Lignes d'objectifs : nécessaires à la heatmap entité × axe du rapport.
    with db_session() as db:
        objective_rows = analysis_repository.hr_objectives_details(db, entity, manager, period)
    meta = {"period": period or "Toutes périodes"}
    return comex_report_service.generate(analytics, objective_rows, meta)
