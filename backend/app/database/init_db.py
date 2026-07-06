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

import logging

from app.core.config import settings
from app.database.base import Base
from app.database.session import engine

# Importer le paquet `models` enregistre TOUTES les tables sur Base.metadata.
import app.models  # noqa: F401

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Crée toutes les tables ORM manquantes (idempotent)."""
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _create_vector_tables()


def _run_migrations() -> None:
    """Migrations légères et idempotentes : `create_all` n'ALTÈRE pas les tables
    existantes. On ajoute ici les colonnes manquantes sur une base déjà peuplée."""
    try:
        with engine.begin() as conn:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()]
            if "active" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
                logger.info("Migration : colonne users.active ajoutée")
    except Exception as e:
        logger.error("Migration users.active échouée: %s", e)


def _create_vector_tables() -> None:
    """Crée la table virtuelle vec0 du RAG (recherche vectorielle locale).

    `vec_rag_chunks` n'est pas un modèle ORM : c'est une table virtuelle
    sqlite-vec, créée en SQL brut et idempotente (IF NOT EXISTS). Son rowid
    correspond à l'id du chunk dans la table `rag_chunks` (jointure au retrieve).

    Défensif : si sqlite-vec n'est pas chargé, on journalise sans bloquer le
    démarrage de l'application.
    """
    dim = settings.RAG_EMBEDDING_DIM
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "CREATE VIRTUAL TABLE IF NOT EXISTS vec_rag_chunks "
                f"USING vec0(embedding float[{dim}])"
            )
    except Exception as e:
        logger.error("Table vectorielle vec_rag_chunks non créée: %s", e)
