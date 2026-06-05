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

    SÉCURITÉ : le rôle n'est PAS accepté côté client. L'inscription publique
    crée systématiquement un compte COLLAB (cf. auth_controller.register).
    La création de comptes MANAGER/HR/ADMIN passe par un endpoint administratif
    dédié, jamais par /api/auth/register.
    """
    email: str
    password: str
    name: str
    manager_id: Optional[str] = None


class UserPublic(BaseModel):
    """Représentation publique d'un utilisateur (jamais le hash du mot de passe)."""
    id: str
    email: str
    name: str
    role: str
    manager_id: Optional[str] = None
    team: Optional[str] = None
