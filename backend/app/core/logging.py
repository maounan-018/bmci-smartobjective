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

import json
import logging
import sys
import time

from app.core.config import settings

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """Formatter JSON une ligne pour ELK/Loki/Datadog."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, datefmt=None),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """Configure le logger racine (idempotent). À appeler une fois au démarrage."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_FORMAT == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    _CONFIGURED = True
