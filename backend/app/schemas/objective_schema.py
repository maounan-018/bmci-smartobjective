#!/usr/bin/env python3
"""
schemas/objective_schema.py — Schémas Pydantic des objectifs.

RÔLE
    Validation/typage des corps de requête pour les objectifs personnels et le
    catalogue stratégique d'entreprise. Aucune logique métier ici.

EMPLACEMENT MVC
    Couche "schemas" : contrats d'entrée/sortie.
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

_TITLE_MAX = 500
_DESC_MAX = 5000
_SHORT_MAX = 100
# Contrôle caractère : rejette les bytes de contrôle (hors \t\n\r) et les
# magic bytes binaires (ex. PK\x03\x04 d'un fichier .xlsx envoyé par erreur).
_CTRL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _validate_text(v: Optional[str]) -> Optional[str]:
    if v is not None and _CTRL_RE.search(v):
        raise ValueError("Le champ contient des caractères binaires non autorisés.")
    return v


class ObjectiveCreate(BaseModel):
    """Création d'un objectif personnel."""
    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default="", max_length=_DESC_MAX)
    context: Optional[str] = Field(default="", max_length=_DESC_MAX)

    _val_title = field_validator("title", "description", "context", mode="before")(_validate_text)


class ObjectiveUpdate(BaseModel):
    """Mise à jour partielle d'un objectif personnel."""
    title: Optional[str] = Field(default=None, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default=None, max_length=_DESC_MAX)
    status: Optional[str] = Field(default=None, max_length=_SHORT_MAX)
    progress: Optional[str] = Field(default=None, max_length=_SHORT_MAX)
    smart_analysis: Optional[dict] = None
    alignment_analysis: Optional[dict] = None

    _val_title = field_validator("title", "description", mode="before")(_validate_text)


class CompanyObjectiveCreate(BaseModel):
    """Création d'un objectif stratégique d'entreprise."""
    id: Optional[str] = Field(default=None, max_length=_SHORT_MAX)
    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default="", max_length=_DESC_MAX)
    department: Optional[str] = Field(default="", max_length=_SHORT_MAX)

    _val_title = field_validator("title", "description", mode="before")(_validate_text)


class CompanyObjectiveUpdate(BaseModel):
    """Mise à jour partielle d'un objectif stratégique d'entreprise."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default=None, max_length=_DESC_MAX)
    department: Optional[str] = Field(default=None, max_length=_SHORT_MAX)

    _val_title = field_validator("title", "description", mode="before")(_validate_text)
