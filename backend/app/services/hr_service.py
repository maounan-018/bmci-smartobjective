#!/usr/bin/env python3
"""
services/hr_service.py — Façade du domaine RH.

Le domaine RH a été scindé en modules cohérents (< 250 lignes chacun) pour la
maintenabilité. Ce module ré-exporte l'API publique afin que les controllers
continuent d'appeler `hr_service.xxx(...)` sans changement :

    - hr_analysis_service : analyses, batch SSE, analytics, détails, historique
    - hr_import_service   : imports Excel (stratégie & objectifs collaborateurs)
    - hr_export_service   : exports Excel/PDF
    - hr_common           : contrôle de rôle partagé (require_hr)

EMPLACEMENT MVC
    Couche "services" : point d'entrée unique du domaine RH.
"""

from app.services.hr_analysis_service import (
    analyze_personal,
    get_analysis_results,
    build_batch_generator,
    get_analytics,
    get_objectives_details,
    get_imports,
)
from app.services.hr_import_service import import_strategy, import_objectives
from app.services.hr_export_service import export_excel, export_pdf

__all__ = [
    "analyze_personal",
    "get_analysis_results",
    "build_batch_generator",
    "get_analytics",
    "get_objectives_details",
    "get_imports",
    "import_strategy",
    "import_objectives",
    "export_excel",
    "export_pdf",
]
