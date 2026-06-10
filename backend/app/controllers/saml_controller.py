#!/usr/bin/env python3
"""
controllers/saml_controller.py — Routes SSO SAML 2.0 (ADFS / Microsoft Entra ID).

ENDPOINTS (préfixe /api/auth/saml)
    GET  /status    : { enabled, simulation } — le frontend affiche le bouton SSO
    GET  /metadata  : XML des métadonnées SP (à transmettre à la DSI)
    GET  /login     : SP-initiated SSO — redirige (302) vers l'IdP (ou la simulation)
    POST /acs        : Assertion Consumer Service — reçoit l'assertion signée,
                       crée la session, redirige vers le frontend avec le token

GRACE DEGRADATION
    Si le SSO n'est pas configuré (.env) ou si python3-saml n'est pas installé,
    les routes renvoient 503 avec un message clair — l'app reste fonctionnelle
    en mode local.

NOTE
    Le mode SIMULATION (dev) est totalement isolé dans
    controllers/saml_simulation_controller.py (monté conditionnellement par main).
    Ce fichier-ci ne contient AUCUN code de simulation : il est prêt pour la prod.

EMPLACEMENT MVC
    Couche "controllers" : endpoints HTTP, logique déléguée aux services/providers.
"""

import secrets
import time

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel

from app.core.config import settings
from app.auth.saml_settings import build_saml_settings
from app.auth.providers.saml_provider import SamlProvider, SamlNotInstalled, extract_profile
from app.services import auth_service
from app.controllers.auth_controller import set_session_cookies
from app.utils.helpers import request_meta

router = APIRouter(prefix="/api/auth/saml", tags=["SSO SAML"])


# --- Code SSO à usage unique : le token de session ne transite JAMAIS dans l'URL.
# L'ACS redirige avec ?sso_code=... ; le frontend l'échange (POST) contre le token.
_SSO_CODE_TTL = 120  # secondes
_sso_codes: dict[str, tuple[str, float]] = {}


def _prune_codes() -> None:
    now = time.time()
    for c in [c for c, (_t, exp) in _sso_codes.items() if exp < now]:
        _sso_codes.pop(c, None)


def issue_sso_code(token: str) -> str:
    """Crée un code à usage unique (TTL court) lié à un token de session."""
    _prune_codes()
    code = secrets.token_urlsafe(24)
    _sso_codes[code] = (token, time.time() + _SSO_CODE_TTL)
    return code


def _consume_sso_code(code: str) -> str | None:
    """Récupère puis invalide le code (usage unique). None si invalide/expiré."""
    _prune_codes()
    entry = _sso_codes.pop(code, None)
    if not entry:
        return None
    token, exp = entry
    return token if time.time() <= exp else None


class _ExchangeRequest(BaseModel):
    code: str


def _prepare(request: Request, post_data: dict | None = None) -> dict:
    """Adapte une requête FastAPI au format attendu par python3-saml.

    Honore X-Forwarded-Proto / X-Forwarded-Host (déploiement derrière reverse proxy).
    """
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    port = host.split(":")[1] if ":" in host else ("443" if proto == "https" else "80")
    return {
        "https": "on" if proto == "https" else "off",
        "http_host": host,
        "server_port": port,
        "script_name": request.url.path,
        "get_data": dict(request.query_params),
        "post_data": post_data or {},
        # ADFS / Microsoft : encodage en minuscules pour la validation de signature.
        "lowercase_urlencoding": True,
    }


def _provider() -> SamlProvider:
    """Instancie le provider si le SP est configuré, sinon 503."""
    if not settings.saml_sp_ready:
        raise HTTPException(status_code=503, detail="SSO SAML non configuré (SP).")
    return SamlProvider(build_saml_settings())


@router.get("/status")
def status():
    """Indique au frontend si le SSO est utilisable (réel ou simulation)."""
    return {
        "enabled": settings.saml_enabled or settings.saml_simulation_active,
        "simulation": settings.saml_simulation_active,
    }


@router.get("/metadata")
def metadata():
    """Métadonnées SP (XML) — à fournir à la DSI pour déclarer l'application."""
    prov = _provider()
    try:
        xml = prov.metadata()
    except SamlNotInstalled as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return Response(content=xml, media_type="application/xml")


@router.get("/login")
def login(request: Request):
    """Démarre le SSO : IdP réel si configuré, sinon page de simulation (dev)."""
    if settings.saml_enabled:
        prov = _provider()
        try:
            url = prov.build_login_url(_prepare(request))
        except SamlNotInstalled as e:
            raise HTTPException(status_code=503, detail=str(e))
        return RedirectResponse(url, status_code=302)
    if settings.saml_simulation_active:
        return RedirectResponse("/api/auth/saml/simulate", status_code=302)
    raise HTTPException(status_code=503, detail="SSO SAML non configuré.")


@router.post("/acs")
async def acs(request: Request):
    """Reçoit l'assertion de l'IdP, crée la session et renvoie vers le frontend."""
    if not settings.saml_enabled:
        raise HTTPException(status_code=503, detail="SSO SAML non configuré.")
    prov = _provider()
    front = settings.SAML_FRONTEND_REDIRECT

    try:
        form = await request.form()
        post_data = {k: v for k, v in form.items()}
        raw = prov.process_response(_prepare(request, post_data))
        profile = extract_profile(raw)
        result = auth_service.login_from_federated(profile, request_meta(request))
        # Code à usage unique en query (PAS le token) ; le front l'échange ensuite.
        code = issue_sso_code(result["token"])
        return RedirectResponse(f"{front}/?sso_code={code}", status_code=302)
    except SamlNotInstalled as e:
        raise HTTPException(status_code=503, detail=str(e))
    except (ValueError, HTTPException):
        # Erreur générique côté client (détail non exposé) — le front affiche un message.
        return RedirectResponse(f"{front}/?sso_error=1", status_code=302)


@router.post("/exchange")
def exchange(payload: _ExchangeRequest, response: Response):
    """Échange un code SSO à usage unique contre la session (cookie HttpOnly posé)."""
    token = _consume_sso_code(payload.code)
    if not token:
        raise HTTPException(status_code=400, detail="Code SSO invalide ou expiré.")
    set_session_cookies(response, token)
    return {"success": True, "token": token}
