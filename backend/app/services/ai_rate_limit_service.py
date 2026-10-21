#!/usr/bin/env python3
"""
services/ai_rate_limit_service.py — Quota d'appels IA (anti-saturation Ollama).

RÔLE
    Borne le nombre d'analyses IA qu'un utilisateur peut déclencher dans une
    fenêtre glissante (cf. .env : AI_RATE_LIMIT_MAX / AI_RATE_LIMIT_WINDOW_SECONDS).
    Au-delà → HTTP 429. Objectif : éviter qu'un seul utilisateur empile des
    requêtes lourdes et sature le modèle local (traité séquentiellement).

    L'état vit EN BASE (table `ai_calls`) : le quota est partagé entre workers et
    survit au redémarrage — comme l'anti brute-force (services/throttle_service).

EMPLACEMENT MVC
    Couche "services" : logique métier (orchestration repository + transaction).
"""

from datetime import datetime, timedelta

from app.core.config import settings
from app.database.session import db_session
from app.repositories import ai_call_repository
from fastapi import HTTPException


def enforce(user_id: str) -> None:
    """Vérifie le quota d'analyses IA de l'utilisateur et enregistre l'appel.

    Lève HTTP 429 si le quota de la fenêtre est déjà atteint (l'appel n'est alors
    PAS enregistré : on ne pénalise pas un utilisateur déjà bloqué)."""
    now = datetime.now()
    window_start = (now - timedelta(seconds=settings.AI_RATE_LIMIT_WINDOW_SECONDS)).isoformat()
    with db_session() as db:
        recent = ai_call_repository.count_since(db, user_id, window_start)
        if recent >= settings.AI_RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Trop d'analyses IA en peu de temps "
                    f"(max {settings.AI_RATE_LIMIT_MAX} par "
                    f"{settings.AI_RATE_LIMIT_WINDOW_SECONDS} s). "
                    f"Patientez quelques instants avant de relancer."
                ),
            )
        ai_call_repository.record(db, user_id, now.isoformat())
        ai_call_repository.prune_before(db, window_start)
