#!/usr/bin/env python3
"""
models/rag_document.py — Modèle ORM `RagDocument` (table `rag_documents`).

RÔLE
    Représente UN document source de la base de connaissances de l'assistant
    (un PDF stratégie, une politique RH, un référentiel...). La RH/admin les
    téléverse via l'UI ; chaque ligne = un fichier importé et ses métadonnées.

    Le contenu textuel n'est pas stocké ici mais découpé en `RagChunk`
    (morceaux) : c'est sur ces morceaux que porte la recherche sémantique.

SÉCURITÉ
    `scope` borne la visibilité d'un document au retrieve (ex: GLOBAL, ou un
    périmètre précis) : on ne mélange pas les connaissances de périmètres
    différents.

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from app.database.base import Base
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Nom du fichier d'origine + titre affiché (par défaut le nom du fichier).
    filename: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # Type de source (pdf, xlsx, txt, md, manual) — informatif (affichage UI).
    source_type: Mapped[str] = mapped_column(String, nullable=False, default="manual")
    # Périmètre de visibilité au retrieve (défaut GLOBAL = visible par tous).
    scope: Mapped[str] = mapped_column(String, nullable=False, default="GLOBAL")
    # État d'ingestion : ready | processing | error.
    status: Mapped[str] = mapped_column(String, nullable=False, default="ready")
    # Nombre de morceaux (chunks) produits à l'ingestion.
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Id de l'utilisateur (RH/admin) ayant téléversé le document — pour l'audit.
    uploaded_by: Mapped[str] = mapped_column(String, nullable=True)
    # Horodatage ISO 8601 (str), cohérent avec le reste du projet.
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    # Chunks du document. Cascade ORM : supprimer le document supprime ses chunks
    # (la suppression des vecteurs vec0 associés est faite explicitement côté
    # service, car vec_rag_chunks n'est pas géré par l'ORM).
    # Forward reference : RagChunk est resolu par la registry SQLAlchemy a runtime.
    chunks: Mapped[list["RagChunk"]] = relationship(  # noqa: F821
        back_populates="document",
        cascade="all, delete-orphan",
    )
