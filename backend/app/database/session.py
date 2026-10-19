#!/usr/bin/env python3
"""
database/session.py — Moteur et sessions SQLAlchemy.

RÔLE
    Crée le moteur (engine) SQLAlchemy pointant sur la base configurée (SQLite
    par défaut, via settings.DB_PATH) et fournit deux façons d'obtenir une
    session ORM :
      - `get_db()`     : dépendance FastAPI (yield) pour les controllers.
      - `db_session()` : gestionnaire de contexte (commit/rollback) pour les
                         services et repositories hors requête HTTP.

    TOUTE la couche d'accès aux données (repositories) passe par une de ces deux
    portes. Aucun `sqlite3` brut ne doit subsister ailleurs dans l'application.

EMPLACEMENT MVC
    Couche "database" : connexion et gestion du cycle de vie des sessions.
"""

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import sqlite_vec

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Construction de l'URL de connexion ---------------------------------------
# On reste sur SQLite (fichier) pour préserver la base existante objectifsmart.db.
# `check_same_thread=False` est nécessaire car FastAPI/Starlette peut servir des
# requêtes depuis plusieurs threads ; chaque session reste néanmoins isolée.
DATABASE_URL = f"sqlite:///{settings.DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)


# --- Extension sqlite-vec : recherche vectorielle du RAG ----------------------
# Les tables virtuelles vec0 (vecteurs d'embeddings) n'existent que si l'extension
# sqlite-vec est chargee dans la connexion courante. On la charge donc sur CHAQUE
# connexion via l'evenement "connect" du moteur. Ce meme moteur est reutilise par
# la suite de tests, qui herite ainsi automatiquement de la recherche vectorielle.
@event.listens_for(engine, "connect")
def _configure_connection(dbapi_connection, connection_record):
    """Configure chaque nouvelle connexion : mode WAL + busy_timeout + sqlite-vec.

    - `journal_mode=WAL` : Write-Ahead Logging. Les LECTURES ne bloquent plus les
      ÉCRITURES et réciproquement, donc un outil externe (DB Browser for SQLite)
      peut consulter/éditer la base pendant que l'appli tourne.
    - `busy_timeout=30000` : si un verrou d'écriture est déjà pris (ex. DB Browser
      en cours de modification), l'appli attend jusqu'à 30 s au lieu d'échouer par
      « database is locked ».
    - `synchronous=NORMAL` : compromis vitesse/durabilité recommandé en WAL.
    - sqlite-vec : extension vectorielle pour le RAG (chargée à chaque connexion).
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
    except Exception as e:  # pragma: no cover
        logger.error("PRAGMA de connexion non appliqués: %s", e)
    finally:
        cursor.close()
    # Extension vectorielle sqlite-vec. Défensif : si elle ne se charge pas
    # (build SQLite sans support, paquet absent), on journalise sans casser la
    # connexion — seules les fonctions RAG échoueront alors, de façon explicite.
    try:
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
        dbapi_connection.enable_load_extension(False)
    except Exception as e:  # pragma: no cover - dépend de l'environnement SQLite
        logger.error("sqlite-vec non chargé (RAG indisponible): %s", e)

# Fabrique de sessions. `expire_on_commit=False` permet de continuer à lire les
# attributs d'un objet après commit (utile pour renvoyer un dict au controller).
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
    future=True,
)


@contextmanager
def db_session() -> Iterator[Session]:
    """
    Transaction ORM : commit si succès, rollback si exception, close systématique.

    Utilisation dans un service :
        with db_session() as db:
            user_repository.create(db, ...)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
