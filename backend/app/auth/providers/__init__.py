#!/usr/bin/env python3
"""
auth/providers/ — Implémentations concrètes de fournisseurs d'identité.

Chaque fournisseur implémente le contrat `IdentityProvider` (cf.
auth/identity_provider.py). Aujourd'hui : `LocalDatabaseProvider`. Demain :
`LDAPProvider` (Active Directory / LDAP de la banque), SSO SAML/OIDC, etc.
"""
