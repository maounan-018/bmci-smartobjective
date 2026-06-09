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
    manager_id: Optional[str] = None  # Obligatoire pour un COLLAB


class RegisterRequest(BaseModel):
    """
    Corps de la requête d'inscription publique.

    SÉCURITÉ : les rôles autorisés à l'inscription publique sont COLLAB,
    MANAGER et HR. Toute autre valeur (ex. ADMIN) est ignorée et ramenée
    à COLLAB côté service (anti-escalade).

    - Un COLLAB DOIT fournir manager_id (son responsable hiérarchique).
    - Un MANAGER ou un HR s'inscrit sans manager_id.
    """
    email: str
    password: str
    name: str
    role: Optional[str] = None         # 'COLLAB' (defaut), 'MANAGER' ou 'HR'
    manager_id: Optional[str] = None


class UserPublic(BaseModel):
    """Représentation publique d'un utilisateur (jamais le hash du mot de passe)."""
    id: str
    email: str
    name: str
    role: str
    manager_id: Optional[str] = None
    team: Optional[str] = None
