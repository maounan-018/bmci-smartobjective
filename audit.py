#!/usr/bin/env python3
"""
audit.py — Module de traçabilité (audit trail) pour ObjectifSMART-AI.

RÔLE
    Centralise l'enregistrement des évènements de sécurité dans la table
    `audit_logs`. Le backend FastAPI est la SEULE source de vérité : tout
    évènement sensible (connexion, échec, déconnexion, accès refusé, action
    sensible, appel IA) doit passer par ce module.

RÈGLES ABSOLUES
    ✅ Autorisé à journaliser : user_id, username, role, type d'évènement,
       statut, IP, user-agent, endpoint, méthode HTTP, description, session_ref.
    ❌ Interdit : mot de passe, token complet, cookie, OTP, clé API, données
       bancaires. Une fonction de filtrage protège contre les fuites accidentelles.

EMPLACEMENT FUTUR (Phase 5 — MVC)
    Ce fichier sera déplacé vers backend/app/services/audit_service.py et
    backend/app/models/audit_log_model.py. Il est isolé ici pour être branché
    immédiatement sans perturber server.py.
"""

import sqlite3
import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional


class AuditEventType(str, Enum):
    """Types d'évènements traçables (cf. cahier des charges)."""
    LOGIN_SUCCESS = "LOGIN_SUCCESS"            # Connexion réussie
    LOGIN_FAILED = "LOGIN_FAILED"              # Tentative échouée
    LOGOUT_MANUAL = "LOGOUT_MANUAL"            # Déconnexion volontaire
    SESSION_EXPIRED = "SESSION_EXPIRED"        # Session expirée/invalide
    ACCESS_DENIED = "ACCESS_DENIED"            # Accès sans authentification valide
    ROLE_ACCESS_DENIED = "ROLE_ACCESS_DENIED"  # Rôle insuffisant
    SENSITIVE_ACTION = "SENSITIVE_ACTION"      # Action critique (import, suppression)
    AI_REQUEST_SENT = "AI_REQUEST_SENT"        # Appel au modèle IA (sans données sensibles)


# Mots-clés interdits dans les descriptions — protection anti-fuite
_FORBIDDEN = (
    "password", "mot_de_passe", "passwd", "pwd", "token", "access_token",
    "cookie", "secret", "api_key", "private_key", "otp", "pin",
)


def init_audit_table(get_conn) -> None:
    """
    Crée la table `audit_logs` et ses index si absents.
    `get_conn` : fonction renvoyant une connexion sqlite3 (injectée par server.py).
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      TEXT,
                username     TEXT,
                role         TEXT,
                event_type   TEXT NOT NULL,
                event_status TEXT DEFAULT 'INFO',
                ip_address   TEXT,
                user_agent   TEXT,
                endpoint     TEXT,
                http_method  TEXT,
                description  TEXT,
                session_ref  TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_logs(event_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_logs(created_at)")
        conn.commit()
    finally:
        conn.close()


def _sanitize(text: Optional[str]) -> Optional[str]:
    """Neutralise une description contenant un mot-clé sensible."""
    if not text:
        return text
    low = text.lower()
    for word in _FORBIDDEN:
        if word in low:
            return "[DESCRIPTION FILTRÉE — contenu potentiellement sensible]"
    return text[:1000]  # Limiter la taille


def session_ref(token: Optional[str]) -> Optional[str]:
    """
    Dérive une référence de session NON sensible à partir du token.
    On ne stocke jamais le token : seulement un hash court (8 caractères),
    suffisant pour corréler des évènements d'une même session.
    """
    if not token:
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]


def log_event(
    get_conn,
    event_type: AuditEventType,
    description: str = "",
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    role: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    endpoint: Optional[str] = None,
    http_method: Optional[str] = None,
    event_status: str = "INFO",
    token: Optional[str] = None,
) -> None:
    """
    Enregistre un évènement d'audit. Ne lève jamais d'exception : un échec
    de journalisation ne doit pas bloquer le flux applicatif principal.

    `get_conn` : fonction renvoyant une connexion sqlite3 (injectée par server.py).
    """
    try:
        conn = get_conn()
        try:
            conn.execute(
                '''INSERT INTO audit_logs
                   (user_id, username, role, event_type, event_status,
                    ip_address, user_agent, endpoint, http_method,
                    description, session_ref, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                (
                    user_id, username, role,
                    event_type.value if isinstance(event_type, AuditEventType) else str(event_type),
                    event_status, ip_address,
                    (user_agent or "")[:500] or None,
                    endpoint, http_method,
                    _sanitize(description),
                    session_ref(token),
                    datetime.now().isoformat(),
                )
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        # Journalisation silencieuse — ne jamais casser la requête utilisateur
        print(f"[AUDIT][WARN] Échec d'écriture du log: {e}")


def fetch_logs(
    get_conn,
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
) -> list:
    """Récupère les logs avec pagination et filtres (route admin uniquement)."""
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params: list = []
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([min(limit, 500), offset])

    conn = get_conn()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
