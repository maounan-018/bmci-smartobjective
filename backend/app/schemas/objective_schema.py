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
from pydantic import BaseModel, Field

_TITLE_MAX = 500
_DESC_MAX = 5000
_SHORT_MAX = 100


class ObjectiveCreate(BaseModel):
    """Création d'un objectif personnel."""
    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default="", max_length=_DESC_MAX)
    context: Optional[str] = Field(default="", max_length=_DESC_MAX)


class ObjectiveUpdate(BaseModel):
    """Mise à jour partielle d'un objectif personnel."""
    title: Optional[str] = Field(default=None, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default=None, max_length=_DESC_MAX)
    status: Optional[str] = Field(default=None, max_length=_SHORT_MAX)
    progress: Optional[str] = Field(default=None, max_length=_SHORT_MAX)
    smart_analysis: Optional[dict] = None
    alignment_analysis: Optional[dict] = None


class CompanyObjectiveCreate(BaseModel):
    """Création d'un objectif stratégique d'entreprise."""
    id: Optional[str] = Field(default=None, max_length=_SHORT_MAX)
    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default="", max_length=_DESC_MAX)
    department: Optional[str] = Field(default="", max_length=_SHORT_MAX)
