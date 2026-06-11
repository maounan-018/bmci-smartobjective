#!/usr/bin/env python3
"""
services/throttle_service.py — Anti brute-force (rate limiting persistant).

RÔLE
    Décide si un identifiant (email OU "ip:<adresse>") peut encore tenter une
    connexion, en s'appuyant sur la table `login_attempts` (et non plus sur un
    dictionnaire en mémoire). Conséquence : le blocage fonctionne en MULTI-WORKER
    (gunicorn -w N) et SURVIT au redémarrage du serveur.

    Politique : au plus `MAX_LOGIN_ATTEMPTS` échecs pendant une fenêtre glissante
    de `LOGIN_LOCKOUT_MINUTES` (cf. .env). Au-delà → 429 côté auth_service.

EMPLACEMENT MVC
    Couche "services" : logique métier (orchestration repository + transaction).
"""

from datetime import datetime, timedelta

from app.core.config import settings
from app.database.session import db_session
from app.repositories import login_attempt_repository


def _window_start_iso(now: datetime | None = None) -> str:
    """Début de la fenêtre glissante (ISO) : maintenant − LOGIN_LOCKOUT_MINUTES."""
    now = now or datetime.now()
    return (now - timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)).isoformat()


def is_login_allowed(identifier: str) -> bool:
    """False si `identifier` a atteint MAX_LOGIN_ATTEMPTS échecs dans la fenêtre."""
    with db_session() as db:
        recent = login_attempt_repository.count_since(db, identifier, _window_start_iso())
    return recent < settings.MAX_LOGIN_ATTEMPTS


def record_failed_login(identifier: str) -> None:
    """Enregistre un échec et purge au passage les lignes hors fenêtre."""
    now = datetime.now()
    with db_session() as db:
        login_attempt_repository.record(db, identifier, now.isoformat())
        login_attempt_repository.prune_before(db, _window_start_iso(now))


def reset_login_attempts(identifier: str) -> None:
    """Réinitialise le compteur après une connexion réussie."""
    with db_session() as db:
        login_attempt_repository.reset(db, identifier)
