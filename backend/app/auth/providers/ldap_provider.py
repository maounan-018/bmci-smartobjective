#!/usr/bin/env python3
"""
auth/providers/ldap_provider.py — Fournisseur d'identité LDAP / Active Directory.

RÔLE
    Squelette prêt à compléter lors de l'intégration avec la DSI de la banque
    (python-ldap / ldap3). Le contrat `IdentityProvider` garantit que les
    services/controllers n'auront RIEN à modifier le jour de la bascule.

COMMENT COMPLÉTER
    1. `authenticate` : bind LDAP avec (user_dn, password), puis lecture des
       attributs (mail, cn, memberOf).
    2. `get_user_groups` : extraction des groupes `memberOf`.
    3. Mapper les groupes via `map_groups_to_role` (cf. identity_provider).

EMPLACEMENT MVC
    Couche "auth" : authentification et récupération de l'identité.
"""

from typing import Optional, List, Dict

from app.auth.identity_provider import IdentityProvider


class LDAPProvider(IdentityProvider):
    """Authentification via LDAP / Active Directory (à implémenter)."""

    def __init__(self, server_url: str, base_dn: str):
        self.server_url = server_url
        self.base_dn = base_dn

    def authenticate(self, credentials: dict) -> Optional[Dict]:
        # TODO (intégration banque) : bind LDAP + lecture attributs (mail, cn, memberOf)
        raise NotImplementedError("Intégration LDAP à implémenter avec la DSI de la banque")

    def get_user_groups(self, external_id: str) -> List[str]:
        raise NotImplementedError("Récupération des groupes LDAP à implémenter")
