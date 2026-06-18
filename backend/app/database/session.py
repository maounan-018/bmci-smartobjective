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
def _load_sqlite_vec(dbapi_connection, connection_record):
    """Active puis charge sqlite-vec, et recoupe le chargement d'extensions.

    Defensif : si l'extension ne peut pas se charger (build SQLite sans support,
    paquet absent...), on journalise une erreur SANS casser la connexion. L'app
    (authentification, objectifs) reste disponible ; seules les fonctions RAG
    echoueront, et de facon explicite.
    """
    try:
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
        dbapi_connection.enable_load_extension(False)
    except Exception as e:  # pragma: no cover - depend de l'environnement SQLite
        logger.error("sqlite-vec non charge (RAG indisponible): %s", e)

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


def get_db() -> Iterator[Session]:
    """
    Dépendance FastAPI : fournit une session ORM et la referme en fin de requête.

    Utilisation dans un controller :
        def endpoint(db: Session = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
