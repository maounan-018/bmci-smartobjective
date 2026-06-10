#!/usr/bin/env python3
"""
services/hr_common.py — Helpers partagés du domaine RH.

Petite brique commune aux services RH (analyse, import, export) pour éviter la
duplication du contrôle de rôle.

EMPLACEMENT MVC
    Couche "services" : logique métier RH (commun).
"""

from fastapi import HTTPException


def require_hr(current_user: dict) -> None:
    """Lève 403 si l'utilisateur n'a pas le rôle HR."""
    if current_user["role"] != "HR":
        raise HTTPException(status_code=403, detail="Accès réservé aux RH.")
