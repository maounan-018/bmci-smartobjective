#!/usr/bin/env python3
"""
schemas/objective_schema.py — Schémas Pydantic des objectifs.

RÔLE
    Validation/typage des corps de requête pour les objectifs personnels et le
    catalogue stratégique d'entreprise. Aucune logique métier ici.

EMPLACEMENT MVC
    Couche "schemas" : contrats d'entrée/sortie.
"""

from typing import Optional
from pydantic import BaseModel


class ObjectiveCreate(BaseModel):
    """Création d'un objectif personnel."""
    title: str
    description: Optional[str] = ""
    context: Optional[str] = ""


class ObjectiveUpdate(BaseModel):
    """Mise à jour partielle d'un objectif personnel."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[str] = None
    smart_analysis: Optional[dict] = None
    alignment_analysis: Optional[dict] = None


class CompanyObjectiveCreate(BaseModel):
    """Création d'un objectif stratégique d'entreprise."""
    id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    department: Optional[str] = ""
