#!/usr/bin/env python3
"""
models/analysis_result.py — Modèles ORM des résultats d'analyse.

RÔLE
    Stocke les résultats d'analyse SMART/alignement. L'isolation stricte par rôle
    impose TROIS tables physiquement séparées (le RH ne voit jamais les analyses
    Manager, et réciproquement ; le collaborateur a sa propre table privée) :
      - `HRAnalysisResult`      -> table `hr_analysis_results`
      - `ManagerAnalysisResult` -> table `manager_analysis_results`
      - `CollabAnalysisResult`  -> table `collab_analysis_results`

    Les trois partagent le même socle de sous-scores SMART (mixin
    `AnalysisResultMixin`). `AnalysisResult` est exposé comme alias du résultat
    « générique » HR pour les usages transverses.

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from sqlalchemy import String, Text, Integer, Float, text
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

from app.database.base import Base


class AnalysisResultMixin:
    """Colonnes communes aux trois tables d'analyse (scores SMART + métadonnées)."""

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    objective_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    objective_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    smart_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    alignment_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    smart_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    alignment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    s_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    m_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    a_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    r_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    t_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issues_count: Mapped[int | None] = mapped_column(Integer, server_default=text("0"))
    top_issue: Mapped[str | None] = mapped_column(Text, nullable=True)

    @declared_attr
    def analyzed_at(cls) -> Mapped[str | None]:  # noqa: N805
        return mapped_column(String, server_default=text("CURRENT_TIMESTAMP"))

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class HRAnalysisResult(AnalysisResultMixin, Base):
    """Résultats d'analyse RH (privés, invisibles pour les managers)."""
    __tablename__ = "hr_analysis_results"


class ManagerAnalysisResult(AnalysisResultMixin, Base):
    """Résultats d'analyse Manager (privés, invisibles pour le RH)."""
    __tablename__ = "manager_analysis_results"

    manager_id: Mapped[str] = mapped_column(String, nullable=False, index=True)


class CollabAnalysisResult(AnalysisResultMixin, Base):
    """Résultats d'analyse personnels du collaborateur (table privée)."""
    __tablename__ = "collab_analysis_results"

    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    objective_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rewrite_fr: Mapped[str | None] = mapped_column(Text, nullable=True)
    rewrite_en: Mapped[str | None] = mapped_column(Text, nullable=True)


# Alias générique pour les usages transverses (le « résultat » par défaut est HR).
AnalysisResult = HRAnalysisResult
