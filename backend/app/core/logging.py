#!/usr/bin/env python3
"""
core/logging.py — Configuration centralisée du logging applicatif.

RÔLE
    Remplace les `print()` éparpillés par un logger structuré (date + niveau +
    module). Le niveau est piloté par `LOG_LEVEL` (.env).

SÉCURITÉ / CONFIDENTIALITÉ
    En production on reste à `INFO`, ce qui MASQUE les logs `DEBUG` : aucune donnée
    RH (réponses du modèle IA, contenu d'objectifs) n'atterrit alors dans les
    journaux. Les détails verbeux sont donc émis en `debug(...)` exclusivement.

USAGE (dans chaque module)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(...) / logger.warning(...) / logger.error(...) / logger.debug(...)

EMPLACEMENT MVC
    Couche "core" : configuration transverse.
"""

import logging
import sys

from app.core.config import settings

_CONFIGURED = False


def setup_logging() -> None:
    """Configure le logger racine (idempotent). À appeler une fois au démarrage."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )
    _CONFIGURED = True
