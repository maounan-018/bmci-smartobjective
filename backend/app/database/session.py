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

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

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
