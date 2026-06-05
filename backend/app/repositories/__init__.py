#!/usr/bin/env python3
"""
repositories/ — Couche d'accès aux données.

RÔLE
    Chaque repository encapsule TOUTES les requêtes SQLAlchemy d'un domaine.
    Aucun accès direct à la base ne doit exister ailleurs (ni dans les
    controllers, ni dans les services). Les fonctions reçoivent une session ORM
    (`db: Session`) ouverte par le service appelant et ne committent jamais
    elles-mêmes (le service gère la transaction via `db_session()`).
"""
