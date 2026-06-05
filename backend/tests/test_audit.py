#!/usr/bin/env python3
"""
tests/test_audit.py — Tests de traçabilité (services/audit_service.py).

Couvre : écriture d'un évènement, filtrage anti-fuite des descriptions
sensibles, référence de session non réversible (jamais le token brut),
et lecture paginée.
"""

from app.services import audit_service as audit
from app.models.audit_log_model import AuditEventType


def test_log_event_and_fetch():
    """Un évènement journalisé doit être relu via fetch_logs."""
    audit.log_event(
        AuditEventType.LOGIN_SUCCESS, "Connexion de Test",
        user_id="u-1", username="user@bmci.test", role="COLLAB",
        event_status="SUCCESS",
    )
    logs = audit.fetch_logs(limit=10)
    assert len(logs) >= 1
    assert logs[0]["event_type"] == AuditEventType.LOGIN_SUCCESS.value
    assert logs[0]["user_id"] == "u-1"


def test_description_sanitization_filters_secrets():
    """Une description contenant un mot-clé sensible est neutralisée."""
    audit.log_event(
        AuditEventType.LOGIN_SUCCESS,
        "le password de l'utilisateur est 1234",
        user_id="u-secret",
    )
    logs = audit.fetch_logs(limit=5, user_id="u-secret")
    assert "1234" not in logs[0]["description"]
    assert "FILTRÉE" in logs[0]["description"]


def test_session_ref_never_exposes_raw_token():
    """La référence de session est un hash court, jamais le token brut."""
    token = "tok_super_secret_value_123456"
    ref = audit.session_ref(token)
    assert ref is not None
    assert ref != token
    assert token not in ref
    assert len(ref) == 8


def test_log_event_never_raises():
    """log_event ne doit jamais lever, même avec des entrées atypiques."""
    audit.log_event(AuditEventType.ACCESS_DENIED, None)  # ne doit pas planter


def test_fetch_logs_filter_by_event_type():
    """Le filtre par type d'évènement doit fonctionner."""
    audit.log_event(AuditEventType.LOGIN_FAILED, "échec", user_id="u-2")
    audit.log_event(AuditEventType.LOGIN_SUCCESS, "ok", user_id="u-2")
    failed = audit.fetch_logs(event_type=AuditEventType.LOGIN_FAILED.value)
    assert all(l["event_type"] == AuditEventType.LOGIN_FAILED.value for l in failed)
