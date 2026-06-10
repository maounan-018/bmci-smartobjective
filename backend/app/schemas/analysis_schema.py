#!/usr/bin/env python3
"""
schemas/analysis_schema.py — Schémas Pydantic des analyses IA.

RÔLE
    Validation/typage des demandes d'analyse SMART, d'alignement stratégique et
    des analyses personnelles Manager.

EMPLACEMENT MVC
    Couche "schemas" : contrats d'entrée/sortie.
"""

from typing import Optional
from pydantic import BaseModel, Field

# Bornes communes : protègent le modèle IA (coût/DoS) et la base.
_TITLE_MAX = 500
_DESC_MAX = 5000


class SmartRequest(BaseModel):
    """Demande d'analyse SMART d'un objectif."""
    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default="", max_length=_DESC_MAX)


class AlignmentRequest(BaseModel):
    """Demande d'analyse d'alignement avec le catalogue stratégique."""
    objectiveTitle: str = Field(min_length=1, max_length=_TITLE_MAX)
    # Cap le nombre d'objectifs envoyés au modèle (anti-DoS / explosion de coût).
    companyObjectives: list = Field(max_length=500)


class ManagerPersonalAnalysisRequest(BaseModel):
    """Analyse SMART de l'objectif personnel d'un manager."""
    title: str = Field(min_length=1, max_length=_TITLE_MAX)
    description: Optional[str] = Field(default="", max_length=_DESC_MAX)
