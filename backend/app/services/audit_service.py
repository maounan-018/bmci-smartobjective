#!/usr/bin/env python3
"""
services/audit_service.py — Service de traçabilité (audit trail).

RÔLE
    Écrit et lit les évènements de sécurité dans `audit_logs` via le repository
    d'audit (SQLAlchemy ORM). Applique le filtrage anti-fuite des descriptions et
    le hachage non réversible de la référence de session. Ne lève jamais lors de
    l'écriture (la journalisation ne doit pas casser une requête métier).

EMPLACEMENT MVC
    Couche "services" : logique métier de journalisation.
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional, List

from app.database.session import db_session
from app.repositories import audit_repository
from app.models.audit_log import AuditEventType

logger = logging.getLogger(__name__)

# Mots-clés interdits dans les descriptions — protection anti-fuite
_FORBIDDEN = (
    "password", "mot_de_passe", "passwd", "pwd", "token", "access_token",
    "cookie", "secret", "api_key", "private_key", "otp", "pin",
)


def init_audit_table() -> None:
    """Crée la table d'audit (et les autres tables manquantes) — idempotent."""
    # L'initialisation du schéma est centralisée dans database/init_db.py.
    from app.database.init_db import init_db
    init_db()


def _sanitize(text_value: Optional[str]) -> Optional[str]:
    """Neutralise une description contenant un mot-clé sensible."""
    if not text_value:
        return text_value
    low = text_value.lower()
    for word in _FORBIDDEN:
        if word in low:
            return "[DESCRIPTION FILTRÉE — contenu potentiellement sensible]"
    return text_value[:1000]


def session_ref(token: Optional[str]) -> Optional[str]:
    """Référence de session NON sensible (hash court, jamais le token brut)."""
    if not token:
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]


def log_event(
    event_type: AuditEventType,
    description: str = "",
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    role: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    endpoint: Optional[str] = None,
    http_method: Optional[str] = None,
    event_status: str = "INFO",
    token: Optional[str] = None,
) -> None:
    """Enregistre un évènement d'audit. Ne lève jamais d'exception."""
    try:
        values = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "event_type": event_type.value if isinstance(event_type, AuditEventType) else str(event_type),
            "event_status": event_status,
            "ip_address": ip_address,
            "user_agent": (user_agent or "")[:500] or None,
            "endpoint": endpoint,
            "http_method": http_method,
            "description": _sanitize(description),
            "session_ref": session_ref(token),
            "created_at": datetime.now().isoformat(),
        }
        with db_session() as db:
            audit_repository.insert(db, values)
    except Exception as e:  # la journalisation ne doit jamais casser la requête
        logger.warning("Échec d'écriture du log d'audit: %s", e)


def fetch_logs(
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[dict]:
    """Récupère les logs avec pagination et filtres (route admin uniquement)."""
    with db_session() as db:
        logs = audit_repository.fetch(
            db, limit=limit, offset=offset, event_type=event_type, user_id=user_id
        )
        return [log.to_dict() for log in logs]
