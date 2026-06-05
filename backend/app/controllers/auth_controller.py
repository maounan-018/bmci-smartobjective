#!/usr/bin/env python3
"""
controllers/auth_controller.py — Routes d'authentification.

RÔLE
    Expose /api/auth/* et la dépendance d'authentification `get_current_user`.
    TOUTE la logique métier est déléguée à `auth_service`. Le controller se limite
    à extraire les métadonnées de requête (pour l'audit), valider la présence du
    token et renvoyer la réponse.

EMPLACEMENT MVC
    Couche "controllers" : routes/endpoints FastAPI, sans logique métier lourde.
"""

from typing import Optional

from fastapi import APIRouter, Request, Header, Depends, HTTPException

from app.schemas.auth_schema import LoginRequest, RegisterRequest
from app.services import auth_service
from app.services import audit_service as audit
from app.models.audit_log import AuditEventType
from app.utils.helpers import request_meta

router = APIRouter(prefix="/api", tags=["Authentification"])


def get_current_user(
    request: Request = None,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Dépendance d'auth : valide le token de session, journalise les refus."""
    ip, ua, endpoint, method = request_meta(request)

    if not authorization:
        audit.log_event(
            AuditEventType.ACCESS_DENIED, "Accès sans token",
            event_status="FAILED", ip_address=ip, user_agent=ua,
            endpoint=endpoint, http_method=method,
        )
        raise HTTPException(status_code=401, detail="Token manquant. Veuillez vous connecter.")

    token = authorization.replace("Bearer ", "")
    user = auth_service.resolve_session_user(token)
    if not user:
        audit.log_event(
            AuditEventType.SESSION_EXPIRED, "Session expirée ou invalide",
            event_status="FAILED", ip_address=ip, user_agent=ua,
            endpoint=endpoint, http_method=method, token=token,
        )
        raise HTTPException(status_code=401, detail="Session expirée ou invalide.")
    return user


@router.post("/auth/register")
def register(request: RegisterRequest, http_request: Request = None):
    """Inscription d'un nouvel utilisateur (toujours COLLAB, anti-escalade)."""
    return auth_service.register(request, request_meta(http_request))


@router.post("/auth/login")
def login(request: LoginRequest, http_request: Request = None):
    """Connexion (token de session)."""
    return auth_service.login(request, request_meta(http_request))


@router.post("/auth/logout")
def logout(http_request: Request = None, current_user: dict = Depends(get_current_user)):
    """Déconnexion volontaire."""
    return auth_service.logout(current_user, request_meta(http_request))


@router.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    """Retourne l'utilisateur authentifié (réhydratation côté frontend)."""
    return {"user": {k: current_user.get(k) for k in ("id", "email", "name", "role", "manager_id", "team")}}
