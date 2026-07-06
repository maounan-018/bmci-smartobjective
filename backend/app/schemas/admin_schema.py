#!/usr/bin/env python3
"""
schemas/admin_schema.py — Schémas Pydantic de l'administration des comptes.

RÔLE
    Validation/typage des corps de requête pour la gestion des utilisateurs
    (création, modification, réinitialisation de mot de passe, activation).
    Réservé au rôle HR/ADMIN (contrôle d'accès côté service). Aucune logique ici.

EMPLACEMENT MVC
    Couche "schemas" : contrats d'entrée/sortie.
"""

from typing import Optional
from pydantic import BaseModel, Field

_ROLE_PATTERN = "^(COLLAB|MANAGER|HR)$"


class AdminUserCreate(BaseModel):
    """Création d'un compte par l'administration."""
    email: str = Field(min_length=3, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    role: str = Field(pattern=_ROLE_PATTERN)
    password: str = Field(min_length=6, max_length=200)
    manager_id: Optional[str] = Field(default=None, max_length=100)
    entity: Optional[str] = Field(default=None, max_length=100)


class AdminUserUpdate(BaseModel):
    """Mise à jour partielle d'un compte (mot de passe et statut à part)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    role: Optional[str] = Field(default=None, pattern=_ROLE_PATTERN)
    manager_id: Optional[str] = Field(default=None, max_length=100)
    entity: Optional[str] = Field(default=None, max_length=100)


class AdminPasswordReset(BaseModel):
    """Réinitialisation du mot de passe d'un compte."""
    password: str = Field(min_length=6, max_length=200)


class AdminActiveUpdate(BaseModel):
    """Activation / désactivation d'un compte."""
    active: bool
