#!/usr/bin/env python3
"""
repositories/hr_import_repository.py — Accès aux données `hr_imports`.

RÔLE
    Journalise et relit l'historique des imports Excel RH.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr_import import HRImport


def create(
    db: Session,
    *,
    import_id: str,
    import_type: str,
    filename: str,
    records_count: int,
    user_id: str,
) -> HRImport:
    """Enregistre un import RH (objectives | strategy)."""
    record = HRImport(
        id=import_id,
        import_type=import_type,
        filename=filename,
        records_count=records_count,
        user_id=user_id,
    )
    db.add(record)
    db.flush()
    return record


def list_recent(db: Session, limit: int = 50) -> List[HRImport]:
    """Historique des imports les plus récents."""
    stmt = select(HRImport).order_by(HRImport.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())
