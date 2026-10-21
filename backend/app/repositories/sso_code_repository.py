#!/usr/bin/env python3
"""
repositories/sso_code_repository.py — Accès aux données `sso_codes`.

RÔLE
    Persiste les codes SSO à usage unique (échangés contre un token de session
    après une assertion SAML vérifiée) afin que le flux fonctionne derrière
    plusieurs workers. Seul le HASH du code est stocké ; la table mappe un code
    vers un `user_id` (jamais un token).

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from typing import Optional

from app.core.security import hash_token
from app.models.sso_code import SsoCode
from sqlalchemy import delete
from sqlalchemy.orm import Session


def create(db: Session, *, code: str, user_id: str, expires_at: str) -> None:
    """Enregistre un code (sous forme hashée) lié à un utilisateur, avec expiration."""
    db.add(SsoCode(code_hash=hash_token(code), user_id=user_id, expires_at=expires_at))


def consume(db: Session, code: str, now_iso: str) -> Optional[str]:
    """
    Récupère et invalide un code en UNE seule opération (usage unique, anti-rejeu
    y compris entre workers : le DELETE atomique garantit qu'un seul appelant
    obtient le user_id). Retourne le `user_id`, ou None si invalide/expiré.
    """
    stmt = (
        delete(SsoCode)
        .where(SsoCode.code_hash == hash_token(code), SsoCode.expires_at > now_iso)
        .returning(SsoCode.user_id)
    )
    row = db.execute(stmt).first()
    return row[0] if row else None


def prune(db: Session, now_iso: str) -> None:
    """Supprime les codes expirés (hygiène, appelée à chaque émission)."""
    db.execute(delete(SsoCode).where(SsoCode.expires_at <= now_iso))
