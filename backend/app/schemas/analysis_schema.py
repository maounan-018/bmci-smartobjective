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
from pydantic import BaseModel


class SmartRequest(BaseModel):
    """Demande d'analyse SMART d'un objectif."""
    title: str
    description: Optional[str] = ""


class AlignmentRequest(BaseModel):
    """Demande d'analyse d'alignement avec le catalogue stratégique."""
    objectiveTitle: str
    companyObjectives: list


class ManagerPersonalAnalysisRequest(BaseModel):
    """Analyse SMART de l'objectif personnel d'un manager."""
    title: str
    description: Optional[str] = ""
