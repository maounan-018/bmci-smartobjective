#!/usr/bin/env python3
"""
utils/helpers.py — Petites fonctions utilitaires transverses.

RÔLE
    Helpers sans dépendance métier, réutilisés par plusieurs controllers/services :
      - conversions sûres (safe_int / safe_float)
      - calcul du score SMART total et validité
      - extraction des métadonnées d'une requête HTTP (pour l'audit)

EMPLACEMENT MVC
    Couche "utils" : fonctions pures, sans état ni accès base.
"""

from typing import Optional

from fastapi import Request


def safe_int(value, default: int = 0) -> int:
    """Retourne un entier sûr, `default` si la valeur est None ou invalide."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default: float = 0.0) -> float:
    """Retourne un float sûr, `default` si la valeur est None ou invalide."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_smart_total(obj) -> int:
    """Calcule le total des 5 sous-scores SMART (s/m/a/r/t) d'un objet."""
    return (
        safe_int(obj.get("s_score")) + safe_int(obj.get("m_score"))
        + safe_int(obj.get("a_score")) + safe_int(obj.get("r_score"))
        + safe_int(obj.get("t_score"))
    )


def is_smart_valid(obj) -> bool:
    """Un objectif est considéré SMART si le total des sous-scores est >= 4."""
    return calculate_smart_total(obj) >= 4


def request_meta(req: Optional[Request]):
    """Extrait (ip_address, user_agent, endpoint, http_method) d'une requête FastAPI."""
    if req is None:
        return (None, None, None, None)
    ip = req.client.host if req.client else None
    ua = req.headers.get("user-agent")
    return (ip, ua, str(req.url.path), req.method)
