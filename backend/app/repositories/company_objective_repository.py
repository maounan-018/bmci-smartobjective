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

from app.models.company_objective import CompanyObjective
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_all(db: Session) -> list[CompanyObjective]:
    """Catalogue stratégique complet, récents d'abord."""
    stmt = select(CompanyObjective).order_by(CompanyObjective.created_at.desc())
    return list(db.scalars(stmt).all())


def list_for_alignment(db: Session) -> list[dict]:
    """Projection {id, title, description} utilisée par l'analyse d'alignement IA."""
    stmt = select(CompanyObjective.id, CompanyObjective.title, CompanyObjective.description)
    return [
        {"id": r.id, "title": r.title, "description": r.description} for r in db.execute(stmt).all()
    ]


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


def get_by_id(db: Session, obj_id: str):
    """Récupère un objectif stratégique par son id (ou None)."""
    return db.get(CompanyObjective, obj_id)


def update(db: Session, obj_id: str, values: dict):
    """Met à jour les champs fournis d'un objectif stratégique (ou None si absent)."""
    obj = db.get(CompanyObjective, obj_id)
    if obj is None:
        return None
    for key, value in values.items():
        setattr(obj, key, value)
    db.flush()
    return obj


def delete_by_id(db: Session, obj_id: str) -> bool:
    """Supprime un objectif stratégique. Retourne True si un objet a été supprimé."""
    obj = db.get(CompanyObjective, obj_id)
    if obj is None:
        return False
    db.delete(obj)
    db.flush()
    return True
