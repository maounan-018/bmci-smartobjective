#!/usr/bin/env python3
"""
schemas/auth_schema.py — Schémas Pydantic d'authentification.

RÔLE
    Validation et typage des données entrantes/sortantes des endpoints d'auth.
    Sépare le contrat d'API de la logique métier (couche "schemas" du MVC).
"""

from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Corps de la requête de connexion."""
    email: str
    password: str


class UserPublic(BaseModel):
    """Représentation publique d'un utilisateur (jamais le hash du mot de passe)."""
    id: str
    email: str
    name: str
    role: str
    manager_id: Optional[str] = None
    team: Optional[str] = None
