#!/usr/bin/env python3
"""
services/auth_service.py — Logique métier d'authentification.

RÔLE
    Orchestrent l'inscription, la connexion, la déconnexion et la résolution de
    session. Délègue :
      - identité      -> auth/identity_provider (local aujourd'hui, LDAP demain)
      - cryptographie -> core/security
      - persistance   -> repositories (users, sessions)
      - traçabilité   -> services/audit_service

    Les controllers se contentent d'appeler ces fonctions ; toute la logique
    sensible (anti-escalade de rôle, rate limiting, migration de hash) vit ici.

EMPLACEMENT MVC
    Couche "services" : logique métier d'authentification.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core import security
from app.database.session import db_session
from app.repositories import user_repository, session_repository
from app.services import audit_service as audit
from app.models.audit_log import AuditEventType
from app.auth.identity_provider import get_identity_provider

# Métadonnées de requête : (ip_address, user_agent, endpoint, http_method)
Meta = Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]
_EMPTY_META: Meta = (None, None, None, None)


def _public_user(user) -> dict:
    """Projection publique (jamais le hash) à partir d'un modèle User ou d'un dict."""
    get = user.get if isinstance(user, dict) else lambda k: getattr(user, k, None)
    return {k: get(k) for k in ("id", "email", "name", "role", "manager_id", "team")}


def resolve_session_user(token: str) -> Optional[dict]:
    """Retourne l'utilisateur (dict) d'une session valide, ou None."""
    with db_session() as db:
        user = user_repository.get_by_valid_session(db, token, datetime.now().isoformat())
        return user.to_dict() if user else None


def register(request, meta: Meta = _EMPTY_META) -> dict:
    """
    Inscription publique. SÉCURITÉ : crée TOUJOURS un compte COLLAB (le rôle n'est
    jamais lu depuis la requête) et exige un manager existant.
    """
    ip, ua, endpoint, method = meta
    role = "COLLAB"  # rôle forcé côté serveur (anti-escalade)

    if not request.manager_id:
        raise HTTPException(
            status_code=400,
            detail="Sélection du manager obligatoire. Veuillez choisir votre manager.",
        )

    user_id = f"user-{secrets.token_hex(4)}"
    pwd_hash = security.hash_password(request.password)
    token = security.generate_token()
    expires = datetime.now() + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)

    try:
        with db_session() as db:
            if not user_repository.is_manager(db, request.manager_id):
                raise HTTPException(status_code=400, detail="Manager invalide.")

            user_repository.create(
                db,
                user_id=user_id,
                email=request.email,
                password_hash=pwd_hash,
                name=request.name,
                role=role,
                manager_id=request.manager_id,
            )
            session_repository.create(db, token, user_id, expires.isoformat())
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    audit.log_event(
        AuditEventType.LOGIN_SUCCESS, f"Inscription de {request.name}",
        user_id=user_id, username=request.email, role=role,
        event_status="SUCCESS", ip_address=ip, user_agent=ua,
        endpoint=endpoint, http_method=method, token=token,
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "email": request.email,
            "name": request.name,
            "role": role,
            "manager_id": request.manager_id,
        },
    }


def login(request, meta: Meta = _EMPTY_META) -> dict:
    """Connexion : rate limiting -> identité -> migration hash -> session -> audit."""
    identifier = (request.email or "").strip().lower()
    ip, ua, endpoint, method = meta

    if not security.is_login_allowed(identifier):
        audit.log_event(
            AuditEventType.LOGIN_FAILED, f"Compte bloqué (trop de tentatives) : {identifier}",
            username=identifier, event_status="FAILED",
            ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method,
        )
        raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez plus tard.")

    # Authentification déléguée au fournisseur d'identité (local aujourd'hui, SSO demain)
    provider = get_identity_provider()
    profile = provider.authenticate({"email": request.email, "password": request.password})

    if not profile:
        security.record_failed_login(identifier)
        audit.log_event(
            AuditEventType.LOGIN_FAILED, f"Échec de connexion : {identifier}",
            username=identifier, event_status="FAILED",
            ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method,
        )
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    security.reset_login_attempts(identifier)
    user_id = profile["external_id"]
    token = security.generate_token()
    expires = datetime.now() + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)

    with db_session() as db:
        user = user_repository.get_by_id(db, user_id)
        # Migration transparente du hash si ancien format SHA-256
        if user and security.needs_rehash(user.password_hash):
            user_repository.update_password_hash(
                db, user_id, security.hash_password(request.password)
            )
        # Session unique : on purge les anciennes puis on en crée une nouvelle
        session_repository.delete_by_user(db, user_id)
        session_repository.create(db, token, user_id, expires.isoformat())
        user_public = _public_user(user)
        username = user.email
        name = user.name
        user_role = user.role

    audit.log_event(
        AuditEventType.LOGIN_SUCCESS, f"Connexion réussie de {name}",
        user_id=user_id, username=username, role=user_role,
        event_status="SUCCESS", ip_address=ip, user_agent=ua,
        endpoint=endpoint, http_method=method, token=token,
    )
    return {"success": True, "token": token, "user": user_public}


def logout(current_user: dict, meta: Meta = _EMPTY_META) -> dict:
    """Déconnexion volontaire : suppression des sessions + audit."""
    ip, ua, endpoint, method = meta
    with db_session() as db:
        session_repository.delete_by_user(db, current_user["id"])
    audit.log_event(
        AuditEventType.LOGOUT_MANUAL, f"Déconnexion de {current_user.get('name')}",
        user_id=current_user["id"], username=current_user.get("email"),
        role=current_user.get("role"), event_status="SUCCESS",
        ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method,
    )
    return {"success": True}
