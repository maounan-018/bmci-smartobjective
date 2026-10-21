#!/usr/bin/env python3
"""
auth/providers/local_provider.py — Fournisseur d'identité local (base SQLite).

RÔLE
    Authentifie un utilisateur contre la base locale via le repository utilisateur
    (SQLAlchemy ORM) et la vérification de mot de passe (core/security). C'est
    l'implémentation par défaut ; en production bancaire, l'authentification
    fédérée SAML 2.0 prend le relais (cf. providers/saml_provider.py).

EMPLACEMENT MVC
    Couche "auth" : authentification et récupération de l'identité.
"""

from typing import Optional

from app.auth.identity_provider import IdentityProvider
from app.core.security import verify_password
from app.database.session import db_session
from app.repositories import user_repository


class LocalDatabaseProvider(IdentityProvider):
    """Authentification via la base locale (provisoire avant intégration IAM)."""

    def authenticate(self, credentials: dict) -> Optional[dict]:
        email = (credentials.get("email") or "").strip()
        password = credentials.get("password") or ""

        with db_session() as db:
            user = user_repository.get_by_email(db, email)
            if not user or not verify_password(password, user.password_hash):
                return None
            return {
                "external_id": user.id,
                "email": user.email,
                "display_name": user.name,
                "groups": [user.role],  # En local : le rôle fait office de groupe
            }

    def get_user_groups(self, external_id: str) -> list[str]:
        with db_session() as db:
            user = user_repository.get_by_id(db, external_id)
            return [user.role] if user else []
