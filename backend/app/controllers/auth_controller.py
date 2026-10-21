#!/usr/bin/env python3
"""
controllers/auth_controller.py — Routes d'authentification.

RÔLE
    Expose /api/auth/* et la dépendance d'authentification `get_current_user`.
    TOUTE la logique métier est déléguée à `auth_service`.

TRANSPORT DE SESSION (mode double)
    - Cookie `session` **HttpOnly** (recommandé, anti-vol XSS) — défini au login/SSO.
    - OU en-tête `Authorization: Bearer <token>` (compat / clients non navigateur).
    Quand l'authentification se fait par COOKIE et que la méthode est mutante
    (POST/PUT/PATCH/DELETE), on exige un jeton CSRF (double-submit cookie) :
    le client renvoie la valeur du cookie `csrf_token` dans l'en-tête `X-CSRF-Token`.
    L'auth par en-tête Bearer n'a pas besoin de CSRF (immunisée par construction).

EMPLACEMENT MVC
    Couche "controllers" : routes/endpoints FastAPI, sans logique métier lourde.
"""

import secrets
from typing import Optional

from app.core.config import settings
from app.models.audit_log import AuditEventType
from app.schemas.auth_schema import LoginRequest
from app.services import audit_service as audit
from app.services import auth_service
from app.utils.helpers import request_meta
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

router = APIRouter(prefix="/api", tags=["Authentification"])

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


# ==================== Cookies de session ====================


def set_session_cookies(response: Response, token: str) -> None:
    """Pose le cookie de session HttpOnly + le cookie CSRF (lisible par le JS)."""
    max_age = settings.TOKEN_EXPIRY_HOURS * 3600
    secure = settings.is_production  # Secure exigé en prod (HTTPS) ; off en dev http
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(24),
        max_age=max_age,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    """Supprime les cookies de session et CSRF (déconnexion)."""
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


# ==================== Dépendance d'authentification ====================


def get_current_user(
    request: Request = None,
    authorization: Optional[str] = Header(None),
) -> dict:
    """Valide la session (cookie HttpOnly OU Bearer) + CSRF si cookie+mutation."""
    ip, ua, endpoint, method = request_meta(request)

    token = None
    via_cookie = False
    if request is not None:
        token = request.cookies.get(SESSION_COOKIE)
        via_cookie = bool(token)
    if not token and authorization:
        token = authorization.removeprefix("Bearer ").strip()

    if not token:
        audit.log_event(
            AuditEventType.ACCESS_DENIED,
            "Accès sans token",
            event_status="FAILED",
            ip_address=ip,
            user_agent=ua,
            endpoint=endpoint,
            http_method=method,
        )
        raise HTTPException(status_code=401, detail="Token manquant. Veuillez vous connecter.")

    # Protection CSRF : uniquement pour l'auth par cookie sur une méthode mutante.
    if via_cookie and request is not None and request.method in _MUTATING_METHODS:
        csrf_cookie = request.cookies.get(CSRF_COOKIE)
        csrf_header = request.headers.get(CSRF_HEADER)
        if (
            not csrf_cookie
            or not csrf_header
            or not secrets.compare_digest(csrf_cookie, csrf_header)
        ):
            audit.log_event(
                AuditEventType.ACCESS_DENIED,
                "Jeton CSRF manquant ou invalide",
                event_status="FAILED",
                ip_address=ip,
                user_agent=ua,
                endpoint=endpoint,
                http_method=method,
            )
            raise HTTPException(status_code=403, detail="Jeton CSRF manquant ou invalide.")

    user = auth_service.resolve_session_user(token)
    if not user:
        audit.log_event(
            AuditEventType.SESSION_EXPIRED,
            "Session expirée ou invalide",
            event_status="FAILED",
            ip_address=ip,
            user_agent=ua,
            endpoint=endpoint,
            http_method=method,
            token=token,
        )
        raise HTTPException(status_code=401, detail="Session expirée ou invalide.")
    return user


# ==================== Routes ====================


@router.post("/auth/login")
def login(request: LoginRequest, response: Response, http_request: Request = None):
    """Connexion : pose le cookie de session HttpOnly (et renvoie le token pour compat)."""
    result = auth_service.login(request, request_meta(http_request))
    set_session_cookies(response, result["token"])
    return result


@router.post("/auth/logout")
def logout(
    response: Response, http_request: Request = None, current_user: dict = Depends(get_current_user)
):
    """Déconnexion volontaire : invalide la session + supprime les cookies."""
    result = auth_service.logout(current_user, request_meta(http_request))
    clear_session_cookies(response)
    return result


@router.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    """Retourne l'utilisateur authentifié (réhydratation côté frontend)."""
    return {
        "user": {
            k: current_user.get(k) for k in ("id", "email", "name", "role", "manager_id", "team")
        }
    }
