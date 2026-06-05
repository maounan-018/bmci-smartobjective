#!/usr/bin/env python3
"""
models/audit_log_model.py — SHIM DE COMPATIBILITÉ (déprécié).

Le modèle d'audit est désormais un vrai modèle ORM dans `models/audit_log.py`.
Ce module est conservé uniquement pour ne pas casser les imports historiques
(`from app.models.audit_log_model import AuditEventType`). À terme, importer
directement depuis `app.models.audit_log`.
"""

from app.models.audit_log import AuditEventType  # noqa: F401

__all__ = ["AuditEventType"]
