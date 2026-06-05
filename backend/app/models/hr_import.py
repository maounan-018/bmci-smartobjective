#!/usr/bin/env python3
"""
models/hr_import.py — Modèle ORM `HRImport` (table `hr_imports`).

RÔLE
    Journalise chaque import Excel réalisé par le RH (objectifs collaborateurs ou
    objectifs stratégiques) : type, fichier source, nombre d'enregistrements et
    auteur. Alimente l'historique des imports (/api/hr/imports).

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from sqlalchemy import String, Integer, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class HRImport(Base):
    __tablename__ = "hr_imports"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    import_type: Mapped[str] = mapped_column(String, nullable=False)  # 'objectives' | 'strategy'
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    records_count: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str | None] = mapped_column(
        String, server_default=text("CURRENT_TIMESTAMP")
    )

    user: Mapped["User | None"] = relationship()  # noqa: F821

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
