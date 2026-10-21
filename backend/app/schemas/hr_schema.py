#!/usr/bin/env python3
"""
schemas/hr_schema.py — Schémas Pydantic du domaine RH.

RÔLE
    Validation/typage des requêtes propres au RH (analyse personnelle). Les
    imports Excel reçoivent des `UploadFile` (gérés directement par le controller).

EMPLACEMENT MVC
    Couche "schemas" : contrats d'entrée/sortie.
"""

from typing import Optional

from pydantic import BaseModel


class HRPersonalAnalysisRequest(BaseModel):
    """Analyse SMART de l'objectif personnel d'un membre RH."""

    title: str
    description: Optional[str] = ""
