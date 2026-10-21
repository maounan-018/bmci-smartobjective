#!/usr/bin/env python3
"""
schemas/user_schema.py — Schémas Pydantic des utilisateurs.

RÔLE
    Représentations publiques des utilisateurs (jamais le hash du mot de passe).

EMPLACEMENT MVC
    Couche "schemas" : contrats d'entrée/sortie.
"""

from typing import Optional

from pydantic import BaseModel


class UserPublic(BaseModel):
    """Représentation publique d'un utilisateur."""

    id: str
    email: str
    name: str
    role: str
    manager_id: Optional[str] = None
    team: Optional[str] = None


class ManagerPublic(BaseModel):
    """Manager exposé à l'inscription (sans email, anti-énumération)."""

    id: str
    name: str
    team: Optional[str] = None
