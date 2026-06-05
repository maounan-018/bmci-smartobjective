#!/usr/bin/env python3
"""
models/session.py — Modèle ORM `Session` (table `sessions`).

RÔLE
    Matérialise une session authentifiée : un token aléatoire associé à un
    utilisateur, avec une date d'expiration. La validité d'une session est
    contrôlée à chaque requête protégée (cf. auth_service.get_current_user).

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from sqlalchemy import String, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Session(Base):
    __tablename__ = "sessions"

    # Le token EST la clé primaire (jamais stocké en clair côté audit : cf. session_ref).
    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str | None] = mapped_column(
        String, server_default=text("CURRENT_TIMESTAMP")
    )

    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821
