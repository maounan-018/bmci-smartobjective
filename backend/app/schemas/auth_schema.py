#!/usr/bin/env python3
"""
schemas/auth_schema.py — Schémas Pydantic d'authentification.

RÔLE
    Validation et typage des données entrantes/sortantes des endpoints d'auth.
    Sépare le contrat d'API de la logique métier (couche "schemas" du MVC).
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Validation email simple, sans dépendance externe (email-validator).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginRequest(BaseModel):
    """Corps de la requête de connexion."""

    email: str = Field(min_length=3, max_length=254)
    # max 128 : borne le coût PBKDF2 (anti-DoS par mot de passe géant).
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        v = (v or "").strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("Format d'email invalide.")
        return v


class UserPublic(BaseModel):
    """Représentation publique d'un utilisateur (jamais le hash du mot de passe)."""

    id: str
    email: str
    name: str
    role: str
    manager_id: Optional[str] = None
    team: Optional[str] = None
