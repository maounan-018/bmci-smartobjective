#!/usr/bin/env python3
"""
database/init_db.py — Initialisation du schéma de la base.

RÔLE
    Crée toutes les tables manquantes à partir des métadonnées ORM
    (`Base.metadata`). Idempotent : `create_all` ne recrée jamais une table
    existante, ce qui préserve les données de `objectifsmart.db`.

    Appelé au démarrage de l'application (cf. main.lifespan) et par la suite de
    tests pour préparer une base temporaire isolée.

EMPLACEMENT MVC
    Couche "database" : amorçage du schéma.
"""

from app.database.base import Base
from app.database.session import engine

# Importer le paquet `models` enregistre TOUTES les tables sur Base.metadata.
import app.models  # noqa: F401


def init_db() -> None:
    """Crée toutes les tables ORM manquantes (idempotent)."""
    Base.metadata.create_all(bind=engine)
