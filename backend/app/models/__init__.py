#!/usr/bin/env python3
"""
models/__init__.py — Agrège tous les modèles ORM.

Importer ce paquet (ou n'importe lequel de ses modèles) garantit que TOUTES les
classes sont enregistrées sur `Base.metadata` avant l'appel à `create_all`, et
que les `relationship` inter-modèles se résolvent correctement.
"""

from app.database.base import Base
from app.models.user import User
from app.models.session import Session
from app.models.sso_code import SsoCode
from app.models.objective import Objective
from app.models.company_objective import CompanyObjective
from app.models.analysis_result import (
    AnalysisResult,
    HRAnalysisResult,
    ManagerAnalysisResult,
    CollabAnalysisResult,
)
from app.models.audit_log import AuditLog, AuditEventType
from app.models.hr_import import HRImport
from app.models.login_attempt import LoginAttempt
from app.models.ai_call import AiCall

__all__ = [
    "Base",
    "User",
    "Session",
    "SsoCode",
    "Objective",
    "CompanyObjective",
    "AnalysisResult",
    "HRAnalysisResult",
    "ManagerAnalysisResult",
    "CollabAnalysisResult",
    "AuditLog",
    "AuditEventType",
    "HRImport",
    "LoginAttempt",
    "AiCall",
]
