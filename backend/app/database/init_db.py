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
    existantes. On applique ici les évolutions de schéma/données sur une base déjà
    peuplée (ordre important : colonnes -> contraintes -> données)."""
    try:
        with engine.begin() as conn:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()]
            if "active" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
                logger.info("Migration : colonne users.active ajoutée")
    except Exception as e:
        logger.error("Migration users.active échouée: %s", e)

    try:
        with engine.begin() as conn:
            _migrate_users_allow_admin(conn)
    except Exception as e:
        logger.error("Migration rôle ADMIN échouée: %s", e)

    try:
        with engine.begin() as conn:
            _migrate_emails(conn)
    except Exception as e:
        logger.error("Migration des emails échouée: %s", e)


def _migrate_users_allow_admin(conn) -> None:
    """Autorise le rôle ADMIN : la contrainte CHECK d'origine ne le permet pas et
    SQLite ne sait pas ALTER une contrainte -> on recrée la table `users`
    (données et index préservés). Idempotent : ne fait rien si ADMIN est déjà permis."""
    row = conn.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    if not row or not row[0] or "ADMIN" in row[0]:
        return
    conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    conn.exec_driver_sql("""
        CREATE TABLE users_new (
            id VARCHAR NOT NULL PRIMARY KEY,
            email VARCHAR NOT NULL,
            password_hash VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            role VARCHAR NOT NULL,
            manager_id VARCHAR,
            team VARCHAR,
            entity VARCHAR,
            active INTEGER NOT NULL DEFAULT 1,
            created_at VARCHAR DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_users_role CHECK (role IN ('COLLAB','MANAGER','HR','ADMIN')),
            FOREIGN KEY(manager_id) REFERENCES users(id)
        )
    """)
    conn.exec_driver_sql(
        "INSERT INTO users_new (id,email,password_hash,name,role,manager_id,team,entity,active,created_at) "
        "SELECT id,email,password_hash,name,role,manager_id,team,entity,COALESCE(active,1),created_at FROM users"
    )
    conn.exec_driver_sql("DROP TABLE users")
    conn.exec_driver_sql("ALTER TABLE users_new RENAME TO users")
    conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")
    conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    logger.info("Migration : table users recréée (rôle ADMIN autorisé)")


def _migrate_emails(conn) -> None:
    """Convertit les emails au format `prenom.nom@bmci.local`. Idempotent :
    seules les adresses non conformes sont converties (dérivées du nom, collisions gérées)."""
    from app.core.emails import is_valid_bnp_email, unique_bnp_email

    rows = conn.exec_driver_sql("SELECT id, name, email FROM users").fetchall()
    taken = {(r[2] or "").strip().lower() for r in rows}
    for uid, name, email in rows:
        current = (email or "").strip().lower()
        if is_valid_bnp_email(current):
            continue
        taken.discard(current)
        new_email = unique_bnp_email(name, taken)
        taken.add(new_email)
        conn.exec_driver_sql("UPDATE users SET email = ? WHERE id = ?", (new_email, uid))
        logger.info("Migration email : %s -> %s", email, new_email)


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
