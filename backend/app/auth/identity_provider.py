#!/usr/bin/env python3
"""
auth/identity_provider.py — Contrat d'identité + fabrique (préparation SSO/IAM).

RÔLE
    Découple la logique applicative du mécanisme d'authentification concret.
    Définit le contrat commun `IdentityProvider`, le mapping groupes bancaires ->
    rôles applicatifs, et la fabrique `get_identity_provider()` pilotée par .env.

    Les implémentations concrètes vivent dans `auth/providers/` :
      - LocalDatabaseProvider (défaut, base locale)
      - SamlProvider          (SSO SAML 2.0, cf. providers/saml_provider.py)

EMPLACEMENT MVC
    Couche "auth" : authentification et récupération de l'identité.
"""

from abc import ABC, abstractmethod
from typing import Optional


class IdentityProvider(ABC):
    """Contrat commun à tout fournisseur d'identité."""

    @abstractmethod
    def authenticate(self, credentials: dict) -> Optional[dict]:
        """
        Valide l'identité et retourne un profil normalisé, ou None.
        Profil attendu : {external_id, email, display_name, groups: [...]}.
        """
        raise NotImplementedError

    @abstractmethod
    def get_user_groups(self, external_id: str) -> list[str]:
        """Retourne les groupes/rôles de l'utilisateur dans le système d'identité."""
        raise NotImplementedError


# Mapping groupes bancaires -> rôles applicatifs (à aligner sur l'AD de la banque)
BANK_GROUP_TO_ROLE = {
    "GRP_COLLABORATEURS": "COLLAB",
    "GRP_MANAGERS": "MANAGER",
    "GRP_RH": "HR",
    "GRP_ADMIN_OBJECTIFS": "ADMIN",
}


def map_groups_to_role(groups: list[str]) -> str:
    """Convertit des groupes bancaires en rôle applicatif (priorité décroissante)."""
    priority = ["ADMIN", "HR", "MANAGER", "COLLAB"]
    assigned = [BANK_GROUP_TO_ROLE.get(g, g) for g in groups]
    for role in priority:
        if role in assigned:
            return role
    return "COLLAB"


def get_identity_provider() -> IdentityProvider:
    """
    Fabrique : retourne le fournisseur d'identité local (authentification par
    mot de passe). L'authentification fédérée SAML ne passe PAS par ce contrat :
    elle suit un flux par redirection dédié (cf. controllers/saml_controller.py).

    Import tardif de l'implémentation pour éviter toute dépendance circulaire
    (le provider importe ce module pour le contrat `IdentityProvider`).
    """
    from app.auth.providers.local_provider import LocalDatabaseProvider

    return LocalDatabaseProvider()
