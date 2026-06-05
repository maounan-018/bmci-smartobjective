#!/usr/bin/env python3
"""
auth/identity_provider.py — Contrat d'identité + fabrique (préparation SSO/IAM).

RÔLE
    Découple la logique applicative du mécanisme d'authentification concret.
    Définit le contrat commun `IdentityProvider`, le mapping groupes bancaires ->
    rôles applicatifs, et la fabrique `get_identity_provider()` pilotée par .env.

    Les implémentations concrètes vivent dans `auth/providers/` :
      - LocalDatabaseProvider (défaut, base locale)
      - LDAPProvider          (Active Directory / LDAP, à activer en production)

EMPLACEMENT MVC
    Couche "auth" : authentification et récupération de l'identité.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class IdentityProvider(ABC):
    """Contrat commun à tout fournisseur d'identité."""

    @abstractmethod
    def authenticate(self, credentials: dict) -> Optional[Dict]:
        """
        Valide l'identité et retourne un profil normalisé, ou None.
        Profil attendu : {external_id, email, display_name, groups: [...]}.
        """
        raise NotImplementedError

    @abstractmethod
    def get_user_groups(self, external_id: str) -> List[str]:
        """Retourne les groupes/rôles de l'utilisateur dans le système d'identité."""
        raise NotImplementedError


# Mapping groupes bancaires -> rôles applicatifs (à aligner sur l'AD de la banque)
BANK_GROUP_TO_ROLE = {
    "GRP_COLLABORATEURS": "COLLAB",
    "GRP_MANAGERS": "MANAGER",
    "GRP_RH": "HR",
    "GRP_ADMIN_OBJECTIFS": "ADMIN",
}


def map_groups_to_role(groups: List[str]) -> str:
    """Convertit des groupes bancaires en rôle applicatif (priorité décroissante)."""
    priority = ["ADMIN", "HR", "MANAGER", "COLLAB"]
    assigned = [BANK_GROUP_TO_ROLE.get(g, g) for g in groups]
    for role in priority:
        if role in assigned:
            return role
    return "COLLAB"


def get_identity_provider() -> IdentityProvider:
    """
    Fabrique : retourne le fournisseur d'identité actif selon .env.
    AUTH_PROVIDER=local (défaut) | ldap (à activer après intégration).

    Import tardif des implémentations pour éviter toute dépendance circulaire
    (les providers importent ce module pour le contrat `IdentityProvider`).
    """
    provider = os.getenv("AUTH_PROVIDER", "local").lower()
    if provider == "ldap":
        from app.auth.providers.ldap_provider import LDAPProvider
        return LDAPProvider(
            server_url=os.getenv("LDAP_SERVER_URL", ""),
            base_dn=os.getenv("LDAP_BASE_DN", ""),
        )
    from app.auth.providers.local_provider import LocalDatabaseProvider
    return LocalDatabaseProvider()
