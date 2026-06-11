#!/usr/bin/env python3
"""
repositories/ai_call_repository.py — Accès aux données `ai_calls`.

RÔLE
    Encapsule les requêtes SQL du rate limiting IA (comptage des appels récents
    d'un utilisateur, enregistrement, purge). Aucune logique métier ici : la
    fenêtre et le quota sont décidés par services/ai_rate_limit_service.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.ai_call import AiCall


def count_since(db: Session, user_id: str, since_iso: str) -> int:
    """Nombre d'appels IA de `user_id` depuis `since_iso` (fenêtre glissante)."""
    stmt = (
        select(func.count())
        .select_from(AiCall)
        .where(AiCall.user_id == user_id, AiCall.called_at > since_iso)
    )
    return int(db.execute(stmt).scalar_one())


def record(db: Session, user_id: str, called_at_iso: str) -> None:
    """Enregistre un appel IA (une ligne)."""
    db.add(AiCall(user_id=user_id, called_at=called_at_iso))


def prune_before(db: Session, cutoff_iso: str) -> None:
    """Purge les appels trop anciens (housekeeping, hors fenêtre)."""
    db.execute(delete(AiCall).where(AiCall.called_at < cutoff_iso))
