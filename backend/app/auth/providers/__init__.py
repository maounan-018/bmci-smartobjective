#!/usr/bin/env python3
"""
auth/providers/ — Implémentations concrètes de fournisseurs d'identité.

Chaque fournisseur implémente le contrat `IdentityProvider` (cf.
auth/identity_provider.py). Aujourd'hui : `LocalDatabaseProvider`.
L'authentification fédérée SAML 2.0 vit dans `saml_provider.py` (flux dédié).
"""
