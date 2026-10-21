#!/usr/bin/env python3
"""
models/__init__.py — Agrège tous les modèles ORM.

Importer ce paquet (ou n'importe lequel de ses modèles) garantit que TOUTES les
classes sont enregistrées sur `Base.metadata` avant l'appel à `create_all`, et
que les `relationship` inter-modèles se résolvent correctement.
"""

from app.database.base import Base
from app.models.ai_call import AiCall
from app.models.analysis_result import (
    AnalysisResult,
    CollabAnalysisResult,
    HRAnalysisResult,
    ManagerAnalysisResult,
)
from app.models.audit_log import AuditEventType, AuditLog
from app.models.company_objective import CompanyObjective
from app.models.hr_import import HRImport
from app.models.login_attempt import LoginAttempt
from app.models.objective import Objective
from app.models.rag_chunk import RagChunk
from app.models.rag_document import RagDocument
from app.models.session import Session
from app.models.sso_code import SsoCode
from app.models.user import User

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
    "RagDocument",
    "RagChunk",
]
