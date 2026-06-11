#!/usr/bin/env python3
"""
core/security.py — Primitives de sécurité (hachage, tokens).

RÔLE
    Source de vérité unique pour les opérations cryptographiques :
      - hachage des mots de passe (PBKDF2-HMAC-SHA256, salé, bibliothèque standard) ;
      - vérification à temps constant + migration depuis l'ancien format SHA-256 ;
      - génération et hachage de tokens de session.

    L'anti brute-force (rate limiting) vit désormais EN BASE, dans
    services/throttle_service.py : l'état est partagé entre workers et survit au
    redémarrage (l'ancien dictionnaire en mémoire ne tenait pas en multi-worker).

POURQUOI PBKDF2 ET PAS SHA-256 SIMPLE
    SHA-256 sans sel est vulnérable aux tables arc-en-ciel et au brute-force GPU.
    PBKDF2 ajoute un sel aléatoire par utilisateur et un coût de calcul élevé.

EMPLACEMENT MVC
    Couche "core" : sécurité transverse, réutilisable par les services.
"""

import hmac
import hashlib
import secrets

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


def hash_token(token: str) -> str:
    """
    Hash non réversible d'un token de session, pour stockage en base.
    Le token étant déjà à haute entropie (256 bits), un SHA-256 simple suffit :
    une fuite de la table `sessions` n'expose alors aucun token réutilisable.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
