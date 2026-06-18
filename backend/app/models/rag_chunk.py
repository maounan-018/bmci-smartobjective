#!/usr/bin/env python3
"""
models/rag_chunk.py — Modèle ORM `RagChunk` (table `rag_chunks`).

RÔLE
    Un MORCEAU (passage) d'un `RagDocument`. On découpe les documents en chunks
    car (1) un document entier est trop volumineux pour être embeddé d'un bloc et
    pour tenir dans le contexte du modèle, et (2) on veut retrouver LE passage
    pertinent, pas tout le document.

    L'embedding (vecteur) de chaque chunk n'est PAS stocké ici : il vit dans la
    table virtuelle `vec_rag_chunks` (sqlite-vec), reliée par `id` == rowid.
    `scope` est dénormalisé depuis le document pour filtrer vite au retrieve.

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from sqlalchemy import String, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    # id == rowid de la table vectorielle vec_rag_chunks (jointure au retrieve).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rag_documents.id"), nullable=False
    )
    # Position du morceau dans le document (0, 1, 2...).
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Contenu textuel du passage.
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Périmètre, dénormalisé depuis le document (filtrage rapide au retrieve).
    scope: Mapped[str] = mapped_column(String, nullable=False, default="GLOBAL")

    document: Mapped["RagDocument"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_rag_chunks_document", "document_id"),
        Index("ix_rag_chunks_scope", "scope"),
    )
