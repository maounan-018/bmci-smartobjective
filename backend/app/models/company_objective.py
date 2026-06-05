#!/usr/bin/env python3
"""
models/company_objective.py — Modèle ORM `CompanyObjective` (table `company_objectives`).

RÔLE
    Catalogue des objectifs stratégiques de l'entreprise (axes BMCI). Sert de
    référentiel pour l'analyse d'alignement des objectifs individuels.

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from sqlalchemy import String, Text, Integer, Float, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class CompanyObjective(Base):
    __tablename__ = "company_objectives"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, server_default=text("1"))
    weight: Mapped[float | None] = mapped_column(Float, server_default=text("1.0"))
    created_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
    import_batch_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(
        String, server_default=text("CURRENT_TIMESTAMP")
    )

    creator: Mapped["User | None"] = relationship()  # noqa: F821

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
