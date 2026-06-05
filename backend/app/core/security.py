#!/usr/bin/env python3
"""
core/security.py — Primitives de sécurité (hachage, tokens, anti brute-force).

RÔLE
    Source de vérité unique pour les opérations cryptographiques :
      - hachage des mots de passe (PBKDF2-HMAC-SHA256, salé, bibliothèque standard) ;
      - vérification à temps constant + migration depuis l'ancien format SHA-256 ;
      - génération de tokens de session ;
      - limitation des tentatives de connexion (rate limiting en mémoire).

POURQUOI PBKDF2 ET PAS SHA-256 SIMPLE
    SHA-256 sans sel est vulnérable aux tables arc-en-ciel et au brute-force GPU.
    PBKDF2 ajoute un sel aléatoire par utilisateur et un coût de calcul élevé.

EMPLACEMENT MVC
    Couche "core" : sécurité transverse, réutilisable par les services.
"""

import time
import hmac
import hashlib
import secrets
from typing import Dict, List

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hache un mot de passe avec PBKDF2-HMAC-SHA256 + sel aléatoire."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, settings.PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${settings.PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def _is_legacy_sha256(stored_hash: str) -> bool:
    """Détecte l'ancien format (SHA-256 simple : 64 caractères hexadécimaux)."""
    return len(stored_hash) == 64 and "$" not in stored_hash


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Vérifie un mot de passe à temps constant.
    Supporte PBKDF2 (nouveau) et SHA-256 simple (legacy, pour migration).
    """
    if not stored_hash:
        return False
    if _is_legacy_sha256(stored_hash):
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy, stored_hash)
    try:
        algo, iterations, salt_hex, hash_hex = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """Indique si le hash doit être migré vers le format PBKDF2."""
    return _is_legacy_sha256(stored_hash)


def generate_token() -> str:
    """Génère un token de session cryptographiquement sûr."""
    return secrets.token_urlsafe(32)


# --- Anti brute-force : tentatives échouées en mémoire (par email/IP) ---
_failed_login_attempts: Dict[str, List[float]] = {}


def is_login_allowed(identifier: str) -> bool:
    """False si l'identifiant a dépassé le nombre de tentatives autorisées."""
    now = time.time()
    window_start = now - (settings.LOGIN_LOCKOUT_MINUTES * 60)
    attempts = [t for t in _failed_login_attempts.get(identifier, []) if t > window_start]
    _failed_login_attempts[identifier] = attempts
    return len(attempts) < settings.MAX_LOGIN_ATTEMPTS


def record_failed_login(identifier: str) -> None:
    """Enregistre une tentative échouée pour le rate limiting."""
    _failed_login_attempts.setdefault(identifier, []).append(time.time())


def reset_login_attempts(identifier: str) -> None:
    """Réinitialise le compteur après une connexion réussie."""
    _failed_login_attempts.pop(identifier, None)
