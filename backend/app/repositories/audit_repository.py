#!/usr/bin/env python3
"""
repositories/audit_repository.py — Accès aux données `audit_logs`.

RÔLE
    Écrit et relit les évènements d'audit. La logique de filtrage anti-fuite et
    de hachage de session reste dans `audit_service` ; ici, uniquement l'accès
    aux données.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def insert(db: Session, values: dict) -> AuditLog:
    """Insère un évènement d'audit (valeurs déjà filtrées par le service)."""
    log = AuditLog(**values)
    db.add(log)
    return log


def fetch(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[AuditLog]:
    """Relit les évènements avec pagination et filtres optionnels."""
    stmt = select(AuditLog)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).offset(offset)
    return list(db.scalars(stmt).all())
