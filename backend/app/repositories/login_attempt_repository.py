#!/usr/bin/env python3
"""
repositories/login_attempt_repository.py — Accès aux données `login_attempts`.

RÔLE
    Encapsule TOUTES les requêtes SQL de l'anti brute-force (comptage des échecs
    récents, enregistrement, réinitialisation, purge). Aucune logique métier ici :
    la fenêtre temporelle et le seuil sont décidés par services/throttle_service.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from app.models.login_attempt import LoginAttempt
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session


def count_since(db: Session, identifier: str, since_iso: str) -> int:
    """Nombre d'échecs pour `identifier` depuis `since_iso` (fenêtre glissante)."""
    stmt = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.identifier == identifier,
            LoginAttempt.attempted_at > since_iso,
        )
    )
    return int(db.execute(stmt).scalar_one())


def record(db: Session, identifier: str, attempted_at_iso: str) -> None:
    """Enregistre un échec (une ligne)."""
    db.add(LoginAttempt(identifier=identifier, attempted_at=attempted_at_iso))


def reset(db: Session, identifier: str) -> None:
    """Efface les échecs d'un identifiant (après connexion réussie)."""
    db.execute(delete(LoginAttempt).where(LoginAttempt.identifier == identifier))


def prune_before(db: Session, cutoff_iso: str) -> None:
    """Purge les lignes trop anciennes (housekeeping, hors fenêtre)."""
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < cutoff_iso))
