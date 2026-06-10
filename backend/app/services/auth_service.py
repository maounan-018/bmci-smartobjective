#!/usr/bin/env python3
"""
services/auth_service.py — Logique métier d'authentification.

RÔLE
    Orchestrent l'inscription, la connexion, la déconnexion et la résolution de
    session. Délègue :
      - identité      -> auth/identity_provider (local) ou SSO SAML (fédéré)
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

from app.core.config import settings
from app.core import security
from app.database.session import db_session
from app.repositories import user_repository, session_repository
from app.services import audit_service as audit
from app.models.audit_log import AuditEventType
from app.auth.identity_provider import get_identity_provider, map_groups_to_role

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


def login(request, meta: Meta = _EMPTY_META) -> dict:
    """Connexion : rate limiting -> identité -> migration hash -> session -> audit."""
    identifier = (request.email or "").strip().lower()
    ip, ua, endpoint, method = meta
    ip_key = f"ip:{ip}" if ip else None

    # SECURITE : en SSO réel, la connexion locale est coupée (anti porte dérobée
    # via comptes seedés). Désactivable/forçable via LOCAL_AUTH_ENABLED.
    if not settings.local_auth_enabled:
        audit.log_event(
            AuditEventType.ACCESS_DENIED, "Connexion locale désactivée (SSO actif)",
            username=identifier, event_status="FAILED",
            ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method,
        )
        raise HTTPException(
            status_code=403,
            detail="Connexion locale désactivée. Utilisez le SSO de l'entreprise.",
        )

    # Anti brute-force : limite par email ET par adresse IP (anti password spraying).
    if not security.is_login_allowed(identifier) or (ip_key and not security.is_login_allowed(ip_key)):
        audit.log_event(
            AuditEventType.LOGIN_FAILED, f"Compte/IP bloqué (trop de tentatives) : {identifier}",
            username=identifier, event_status="FAILED",
            ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method,
        )
        raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez plus tard.")

    # Authentification déléguée au fournisseur d'identité (local aujourd'hui, SSO demain)
    provider = get_identity_provider()
    profile = provider.authenticate({"email": request.email, "password": request.password})

    if not profile:
        security.record_failed_login(identifier)
        if ip_key:
            security.record_failed_login(ip_key)
        audit.log_event(
            AuditEventType.LOGIN_FAILED, f"Échec de connexion : {identifier}",
            username=identifier, event_status="FAILED",
            ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method,
        )
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    security.reset_login_attempts(identifier)
    if ip_key:
        security.reset_login_attempts(ip_key)
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


# Rôles acceptés en base (la contrainte CHECK du modèle User interdit ADMIN).
_ALLOWED_DB_ROLES = {"COLLAB", "MANAGER", "HR"}


def provision_federated_user(profile: dict, meta: Meta = _EMPTY_META) -> str:
    """
    JIT provisioning via un fournisseur fédéré (SAML/SSO). Aucun mot de passe :
    on fait confiance à l'assertion déjà vérifiée par le provider.

    Vérifie l'autorisation (groupes), déduit le rôle et crée le compte s'il est
    inconnu (mot de passe aléatoire inutile : le login local reste impossible
    pour ces comptes SSO). NE crée AUCUNE session : le flux SSO ouvre la session
    plus tard, à l'échange du code (cf. start_federated_session). Idempotent : un
    email déjà connu réutilise le compte existant (rôle conservé). Retourne l'id.
    """
    ip, ua, endpoint, method = meta
    email = (profile.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="SSO: email absent de l'assertion.")

    groups = profile.get("groups", [])

    # Filtre d'autorisation optionnel : si SAML_ALLOWED_GROUPS est défini, on
    # refuse tout utilisateur n'appartenant à aucun groupe autorisé (anti porte ouverte).
    if settings.SAML_ALLOWED_GROUPS and not any(g in settings.SAML_ALLOWED_GROUPS for g in groups):
        audit.log_event(
            AuditEventType.ACCESS_DENIED, f"SSO refusé (groupe non autorisé) : {email}",
            username=email, event_status="FAILED",
            ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method,
        )
        raise HTTPException(status_code=403, detail="Accès non autorisé : groupe requis manquant.")

    # Rôle déduit des groupes ; ADMIN ramené à HR (interdit en base, mais HR fait
    # office d'admin), tout le reste -> COLLAB par sécurité.
    role = map_groups_to_role(groups)
    if role not in _ALLOWED_DB_ROLES:
        role = "HR" if role == "ADMIN" else "COLLAB"

    with db_session() as db:
        user = user_repository.get_by_email(db, email)
        if not user:
            user_id = f"saml-{secrets.token_hex(4)}"
            user_repository.create(
                db,
                user_id=user_id,
                email=email,
                password_hash=security.hash_password(secrets.token_urlsafe(32)),
                name=profile.get("display_name") or email,
                role=role,
            )
            user = user_repository.get_by_id(db, user_id)
        return user.id


def start_federated_session(user_id: str, meta: Meta = _EMPTY_META) -> dict:
    """
    Ouvre une session pour un utilisateur DÉJÀ provisionné via SSO (2e temps du
    flux fédéré, déclenché à l'échange du code SSO). Le token brut est renvoyé à
    l'appelant et n'est jamais stocké en clair (cf. session_repository).
    """
    ip, ua, endpoint, method = meta
    token = security.generate_token()
    expires = datetime.now() + timedelta(hours=settings.TOKEN_EXPIRY_HOURS)

    with db_session() as db:
        user = user_repository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="SSO: utilisateur introuvable.")
        session_repository.delete_by_user(db, user.id)
        session_repository.create(db, token, user.id, expires.isoformat())
        user_public = _public_user(user)
        uid, uemail, uname, urole = user.id, user.email, user.name, user.role

    audit.log_event(
        AuditEventType.LOGIN_SUCCESS, f"Connexion SSO SAML de {uname}",
        user_id=uid, username=uemail, role=urole, event_status="SUCCESS",
        ip_address=ip, user_agent=ua, endpoint=endpoint, http_method=method, token=token,
    )
    return {"success": True, "token": token, "user": user_public}


def login_from_federated(profile: dict, meta: Meta = _EMPTY_META) -> dict:
    """
    Connexion fédérée en un seul appel : provisionne l'utilisateur puis ouvre la
    session. Conservé pour les appels directs (et les tests) ; le flux SSO réel
    scinde les deux étapes (provision à l'ACS, session à l'échange du code) afin
    qu'aucun token de session ne soit conservé entre les deux requêtes.
    """
    user_id = provision_federated_user(profile, meta)
    return start_federated_session(user_id, meta)


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
