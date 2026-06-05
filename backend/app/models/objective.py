#!/usr/bin/env python3
"""
models/objective.py — Modèle ORM `Objective` (table `objectives`).

RÔLE
    Représente un objectif annuel d'un collaborateur (ou importé par le RH). Porte
    le texte de l'objectif, son contexte, ses analyses SMART/alignement (stockées
    en JSON sérialisé TEXT) et les métadonnées d'isolation par périmètre
    (`data_scope`, `import_batch_id`) qui séparent strictement les vues HR / MANAGER.

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from sqlalchemy import String, Text, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Objective(Base):
    __tablename__ = "objectives"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str | None] = mapped_column(String, server_default=text("'draft'"))
    progress: Mapped[str | None] = mapped_column(
        String, server_default=text("'not_started'")
    )

    # Analyses IA sérialisées en JSON (TEXT). Parsées par la couche service.
    smart_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    alignment_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_by_role: Mapped[str | None] = mapped_column(String, nullable=True)
    analyzed_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # Périmètre d'isolation (COLLAB par défaut ; 'HR' marque les imports RH).
    data_scope: Mapped[str | None] = mapped_column(String, server_default=text("'COLLAB'"))
    entity: Mapped[str | None] = mapped_column(String, nullable=True)
    manager_name: Mapped[str | None] = mapped_column(String, nullable=True)
    period: Mapped[str | None] = mapped_column(String, nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[str | None] = mapped_column(
        String, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[str | None] = mapped_column(
        String, server_default=text("CURRENT_TIMESTAMP")
    )

    user: Mapped["User"] = relationship(back_populates="objectives")  # noqa: F821

    def to_dict(self) -> dict:
        """Représentation dict brute (analyses encore au format JSON TEXT)."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
