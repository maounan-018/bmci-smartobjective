#!/usr/bin/env python3
"""
repositories/session_repository.py — Accès aux données `sessions`.

RÔLE
    Gère le cycle de vie des sessions authentifiées (création, purge par
    utilisateur). La validation d'une session lors d'une requête protégée est
    faite par `user_repository.get_by_valid_session` (jointure users↔sessions).

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from app.core.security import hash_token
from app.models.session import Session as SessionModel
from sqlalchemy import delete
from sqlalchemy.orm import Session


def create(db: Session, token: str, user_id: str, expires_at: str) -> SessionModel:
    """Crée une session. Seul le HASH du token est stocké (jamais le token brut)."""
    session = SessionModel(token=hash_token(token), user_id=user_id, expires_at=expires_at)
    db.add(session)
    return session


def delete_by_user(db: Session, user_id: str) -> None:
    """Supprime toutes les sessions d'un utilisateur (login/logout)."""
    db.execute(delete(SessionModel).where(SessionModel.user_id == user_id))
    db.flush()
