#!/usr/bin/env python3
"""
schemas/business_schema.py — SHIM DE COMPATIBILITÉ (déprécié).

Les schémas métier sont désormais répartis par domaine :
    - schemas/objective_schema.py  (ObjectiveCreate, ObjectiveUpdate, CompanyObjectiveCreate)
    - schemas/analysis_schema.py   (SmartRequest, AlignmentRequest, ManagerPersonalAnalysisRequest)
    - schemas/hr_schema.py         (HRPersonalAnalysisRequest)

Ce module réexporte l'ensemble pour ne pas casser les imports historiques.
"""

from app.schemas.objective_schema import (  # noqa: F401
    ObjectiveCreate,
    ObjectiveUpdate,
    CompanyObjectiveCreate,
)
from app.schemas.analysis_schema import (  # noqa: F401
    SmartRequest,
    AlignmentRequest,
    ManagerPersonalAnalysisRequest,
)
from app.schemas.hr_schema import HRPersonalAnalysisRequest  # noqa: F401

__all__ = [
    "ObjectiveCreate",
    "ObjectiveUpdate",
    "CompanyObjectiveCreate",
    "SmartRequest",
    "AlignmentRequest",
    "ManagerPersonalAnalysisRequest",
    "HRPersonalAnalysisRequest",
]
