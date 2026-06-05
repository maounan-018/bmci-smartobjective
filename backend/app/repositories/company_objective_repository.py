#!/usr/bin/env python3
"""
repositories/company_objective_repository.py — Accès aux données `company_objectives`.

RÔLE
    Encapsule les requêtes sur le catalogue stratégique d'entreprise : lecture
    complète, projection légère pour l'alignement IA, création et upsert lors des
    imports RH.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_objective import CompanyObjective


def list_all(db: Session) -> List[CompanyObjective]:
    """Catalogue stratégique complet, récents d'abord."""
    stmt = select(CompanyObjective).order_by(CompanyObjective.created_at.desc())
    return list(db.scalars(stmt).all())


def list_for_alignment(db: Session) -> List[dict]:
    """Projection {id, title, description} utilisée par l'analyse d'alignement IA."""
    stmt = select(
        CompanyObjective.id, CompanyObjective.title, CompanyObjective.description
    )
    return [{"id": r.id, "title": r.title, "description": r.description} for r in db.execute(stmt).all()]


def create(db: Session, **fields) -> CompanyObjective:
    """Crée un objectif stratégique."""
    obj = CompanyObjective(**fields)
    db.add(obj)
    db.flush()
    return obj


def merge(db: Session, values: dict) -> CompanyObjective:
    """Upsert par clé primaire (équivalent INSERT OR REPLACE)."""
    obj = db.merge(CompanyObjective(**values))
    db.flush()
    return obj
