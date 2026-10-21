#!/usr/bin/env python3
"""
services/embedding_service.py — Génération d'embeddings locaux (Ollama bge-m3).

RÔLE
    Transforme un texte en vecteur numérique (embedding) via le modèle local
    bge-m3 servi par Ollama. Ces vecteurs alimentent la recherche sémantique du
    RAG (stockés dans la table vectorielle vec0 `vec_rag_chunks`).

    UNIQUE point d'appel à l'API d'embeddings : tout passe par `embed_text` /
    `embed_batch`, jamais d'appel HTTP direct ailleurs.

SÉCURITÉ
    100% local : aucune donnée ne quitte l'infrastructure (conforme CNDP).
    L'URL et le modèle proviennent de la config (.env), jamais codés en dur.

EMPLACEMENT MVC
    Couche "services" : logique métier (embeddings), sans route HTTP.
"""

import logging

import requests
from app.core.config import settings
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Endpoint d'embeddings dérivé de l'URL Ollama (.../api/generate -> .../api/embeddings),
# même convention que la sonde /health/ready dans main.py.
_EMBED_URL = f"{settings.OLLAMA_URL.split('/api/')[0]}/api/embeddings"

# Timeout généreux mais borné : bge-m3 est léger (< 1 s par texte en régime
# normal) ; le tout premier appel peut être plus long (chargement du modèle).
_EMBED_TIMEOUT = 60


def embed_text(text: str) -> list[float]:
    """Renvoie l'embedding (liste de floats) d'un texte via bge-m3.

    Lève une HTTPException si Ollama est injoignable (503), trop lent (504) ou
    renvoie une réponse inattendue (500). Vérifie la dimension du vecteur pour
    détecter au plus tôt une incohérence de modèle (évite de corrompre vec0).
    """
    if not text or not text.strip():
        raise ValueError("embed_text: texte vide")

    try:
        response = requests.post(
            _EMBED_URL,
            json={"model": settings.OLLAMA_EMBED_MODEL, "prompt": text},
            timeout=_EMBED_TIMEOUT,
        )
        response.raise_for_status()
        vector = response.json().get("embedding")
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Ollama n'est pas démarré. Lancez 'ollama serve' puis réessayez.",
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504, detail="Le modèle d'embedding met trop de temps à répondre."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur d'embedding Ollama: %s", e)
        raise HTTPException(
            status_code=500, detail="Erreur interne lors de la génération de l'embedding."
        )

    if not vector or not isinstance(vector, list):
        logger.error("Embedding vide ou invalide (modèle '%s').", settings.OLLAMA_EMBED_MODEL)
        raise HTTPException(status_code=500, detail="Réponse d'embedding invalide.")

    if len(vector) != settings.RAG_EMBEDDING_DIM:
        # Dimension inattendue = mauvais modèle d'embedding configuré : on échoue
        # tôt et clairement plutôt que de corrompre la table vectorielle vec0.
        logger.error(
            "Dimension d'embedding inattendue: %d (attendu %d). Modèle '%s' ?",
            len(vector),
            settings.RAG_EMBEDDING_DIM,
            settings.OLLAMA_EMBED_MODEL,
        )
        raise HTTPException(
            status_code=500, detail="Dimension d'embedding incohérente avec la configuration."
        )

    return vector


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embedde une liste de textes (séquentiel) — renvoie une liste de vecteurs.

    L'API d'embeddings d'Ollama traite un texte à la fois ; on boucle. Pour de
    gros volumes on pourra paralléliser plus tard (au prix d'une charge accrue
    sur Ollama, qui sert en série)."""
    return [embed_text(t) for t in texts]
