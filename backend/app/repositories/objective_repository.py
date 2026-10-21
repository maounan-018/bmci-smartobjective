#!/usr/bin/env python3
"""
repositories/objective_repository.py — Accès aux données `objectives`.

RÔLE
    Encapsule toutes les requêtes ORM sur les objectifs personnels/importés :
    CRUD, filtres de périmètre (isolation HR/MANAGER), agrégations d'équipe et
    mise à jour des analyses. Le parsing JSON des analyses reste au niveau service.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from collections.abc import Sequence
from typing import Optional

from app.models.objective import Objective
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session, selectinload


def get(db: Session, obj_id: str) -> Optional[Objective]:
    """Retourne un objectif par id."""
    return db.get(Objective, obj_id)


def get_with_user(db: Session, obj_id: str) -> Optional[Objective]:
    """Retourne un objectif avec son utilisateur chargé (eager)."""
    stmt = select(Objective).options(selectinload(Objective.user)).where(Objective.id == obj_id)
    return db.scalars(stmt).first()


def list_by_user_ids(db: Session, user_ids: Sequence[str]) -> list[Objective]:
    """Objectifs des utilisateurs donnés (utilisateur chargé), récents d'abord."""
    if not user_ids:
        return []
    stmt = (
        select(Objective)
        .options(selectinload(Objective.user))
        .where(Objective.user_id.in_(user_ids))
        .order_by(Objective.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def list_team_active(db: Session, team_ids: Sequence[str]) -> list[Objective]:
    """
    Objectifs d'équipe pour la vue MANAGER : exclut les objectifs importés/analysés
    par le RH (data_scope='HR' ou import_batch_id LIKE 'obj-%').
    """
    if not team_ids:
        return []
    stmt = (
        select(Objective)
        .options(selectinload(Objective.user))
        .where(
            Objective.user_id.in_(team_ids),
            or_(Objective.data_scope.is_(None), Objective.data_scope != "HR"),
            or_(Objective.import_batch_id.is_(None), Objective.import_batch_id.not_like("obj-%")),
        )
        .order_by(Objective.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def create(db: Session, **fields) -> Objective:
    """Crée un objectif à partir des champs fournis."""
    obj = Objective(**fields)
    db.add(obj)
    db.flush()
    return obj


def update_fields(db: Session, obj_id: str, values: dict) -> None:
    """Met à jour partiellement un objectif (dict colonne -> valeur)."""
    if values:
        db.execute(update(Objective).where(Objective.id == obj_id).values(**values))


def delete_by_id(db: Session, obj_id: str) -> None:
    """Supprime un objectif par id."""
    db.execute(delete(Objective).where(Objective.id == obj_id))


def merge(db: Session, values: dict) -> Objective:
    """Upsert par clé primaire (équivalent INSERT OR REPLACE)."""
    obj = db.merge(Objective(**values))
    db.flush()
    return obj


# ---- Agrégations d'équipe -----------------------------------------------------


def count_by_user_ids(db: Session, user_ids: Sequence[str]) -> int:
    """Nombre total d'objectifs pour un ensemble d'utilisateurs."""
    if not user_ids:
        return 0
    stmt = select(func.count()).select_from(Objective).where(Objective.user_id.in_(user_ids))
    return int(db.scalar(stmt) or 0)


def get_smart_analyses(db: Session, user_ids: Sequence[str]) -> list[str]:
    """JSON bruts des analyses SMART non nulles pour un ensemble d'utilisateurs."""
    if not user_ids:
        return []
    stmt = select(Objective.smart_analysis).where(
        Objective.user_id.in_(user_ids), Objective.smart_analysis.is_not(None)
    )
    return list(db.scalars(stmt).all())


def get_alignment_analyses(db: Session, user_ids: Sequence[str]) -> list[str]:
    """JSON bruts des analyses d'alignement non nulles."""
    if not user_ids:
        return []
    stmt = select(Objective.alignment_analysis).where(
        Objective.user_id.in_(user_ids), Objective.alignment_analysis.is_not(None)
    )
    return list(db.scalars(stmt).all())


def get_progress_counts(db: Session, user_ids: Sequence[str]) -> list[tuple]:
    """Répartition (progress, count) des objectifs d'un ensemble d'utilisateurs."""
    if not user_ids:
        return []
    stmt = (
        select(Objective.progress, func.count())
        .where(Objective.user_id.in_(user_ids))
        .group_by(Objective.progress)
    )
    return list(db.execute(stmt).all())


# ---- Sélection pour analyse en lot (RH) --------------------------------------


def list_unanalyzed_hr(db: Session, limit: int = 100) -> list[Objective]:
    """Objectifs RH non encore analysés (smart_analysis NULL), bornés."""
    stmt = (
        select(Objective)
        .where(
            Objective.smart_analysis.is_(None),
            or_(Objective.data_scope == "HR", Objective.import_batch_id.like("obj-%")),
        )
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def list_hr_by_ids(db: Session, obj_ids: Sequence[str]) -> list[Objective]:
    """Objectifs RH ciblés par id (filtrés sur le périmètre HR)."""
    if not obj_ids:
        return []
    stmt = select(Objective).where(
        Objective.id.in_(obj_ids),
        or_(Objective.data_scope == "HR", Objective.import_batch_id.like("obj-%")),
    )
    return list(db.scalars(stmt).all())


def list_hr_all(db: Session, limit: int = 500) -> list[Objective]:
    """TOUS les objectifs RH (pour une ré-analyse forcée), bornés."""
    stmt = (
        select(Objective)
        .where(or_(Objective.data_scope == "HR", Objective.import_batch_id.like("obj-%")))
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
