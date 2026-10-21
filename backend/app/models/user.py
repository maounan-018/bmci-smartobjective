#!/usr/bin/env python3
"""
models/user.py — Modèle ORM `User` (table `users`).

RÔLE
    Représente un compte applicatif (COLLAB, MANAGER, HR — ADMIN réservé à
    l'évolution future). Source de vérité de l'identité locale et du rattachement
    hiérarchique (manager_id auto-référence vers un autre utilisateur).

NOTE DE FIDÉLITÉ AU SCHÉMA
    Les identifiants sont des chaînes (`user-xxxx`), pas des entiers, et les dates
    sont stockées en TEXT (ISO / CURRENT_TIMESTAMP) comme dans la base existante.
    On conserve ces types pour ne casser ni les données ni le contrat d'API.

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from app.database.base import Base
from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # Rôle applicatif : COLLAB, MANAGER, HR (ADMIN à venir)
    role: Mapped[str] = mapped_column(String, nullable=False)
    manager_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    team: Mapped[str | None] = mapped_column(String, nullable=True)
    entity: Mapped[str | None] = mapped_column(String, nullable=True)
    # Compte actif (1) ou désactivé (0) : un compte désactivé ne peut plus se
    # connecter mais ses données (objectifs, analyses) sont conservées.
    active: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[str | None] = mapped_column(String, server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        CheckConstraint("role IN ('COLLAB', 'MANAGER', 'HR', 'ADMIN')", name="ck_users_role"),
    )

    # --- Relations ---
    # Auto-référence : un manager encadre plusieurs collaborateurs.
    manager: Mapped["User | None"] = relationship(
        "User", remote_side="User.id", back_populates="subordinates"
    )
    subordinates: Mapped[list["User"]] = relationship("User", back_populates="manager")

    objectives: Mapped[list["Objective"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Représentation dict (jamais le hash en sortie d'API)."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "manager_id": self.manager_id,
            "team": self.team,
            "entity": self.entity,
            "active": bool(self.active),
            "created_at": self.created_at,
        }
