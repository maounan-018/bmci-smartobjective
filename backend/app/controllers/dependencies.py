#!/usr/bin/env python3
"""
controllers/dependencies.py — Dépendances FastAPI transverses.

RÔLE
    Regroupe les dépendances réutilisées par plusieurs controllers. Pour l'instant :
    `ai_rate_limited_user`, qui authentifie l'utilisateur (via get_current_user)
    PUIS applique le quota d'appels IA (anti-saturation d'Ollama). Les routes qui
    sollicitent le modèle l'utilisent à la place de `get_current_user`.

EMPLACEMENT MVC
    Couche "controllers" : dépendances/branchements HTTP, sans logique métier
    (déléguée à services/ai_rate_limit_service).
"""

from app.controllers.auth_controller import get_current_user
from app.services import ai_rate_limit_service
from fastapi import Depends


def ai_rate_limited_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Authentifie ET applique le quota d'appels IA (HTTP 429 si dépassé).

    Retourne le même dict utilisateur que `get_current_user` : les routes gardent
    `current_user: dict = Depends(ai_rate_limited_user)` sans autre changement."""
    ai_rate_limit_service.enforce(current_user["id"])
    return current_user
