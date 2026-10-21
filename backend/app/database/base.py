#!/usr/bin/env python3
"""
database/base.py — Base déclarative SQLAlchemy.

RÔLE
    Définit la classe `Base` dont héritent TOUS les modèles ORM (couche models/).
    C'est l'unique point d'enregistrement des métadonnées (Base.metadata) utilisé
    par `init_db.py` pour créer les tables.

POURQUOI UN FICHIER DÉDIÉ
    Isoler `Base` ici évite les imports circulaires : les modèles importent
    uniquement `app.database.base`, jamais `session.py` (qui, lui, importe les
    modèles au moment de l'initialisation).

EMPLACEMENT MVC
    Couche "database" : socle de l'ORM.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe de base déclarative commune à tous les modèles ORM."""

    pass
