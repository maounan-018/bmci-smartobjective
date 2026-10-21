#!/usr/bin/env python3
"""
models/audit_log.py — Modèle ORM `AuditLog` (table `audit_logs`) + types d'évènements.

RÔLE
    Trace les évènements de sécurité. RÈGLE ABSOLUE : ne jamais stocker mot de
    passe, token complet, cookie, OTP ni clé API. Seul un `session_ref` (hash
    court non réversible) est conservé (cf. audit_service).

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from enum import Enum

from app.database.base import Base
from sqlalchemy import Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column


class AuditEventType(str, Enum):
    """Types d'évènements de sécurité traçables."""

    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT_MANUAL = "LOGOUT_MANUAL"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    ROLE_ACCESS_DENIED = "ROLE_ACCESS_DENIED"
    SENSITIVE_ACTION = "SENSITIVE_ACTION"
    AI_REQUEST_SENT = "AI_REQUEST_SENT"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_status: Mapped[str | None] = mapped_column(String, server_default=text("'INFO'"))
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String, nullable=True)
    http_method: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(
        String, index=True, server_default=text("CURRENT_TIMESTAMP")
    )

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
