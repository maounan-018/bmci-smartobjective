#!/usr/bin/env python3
"""
controllers/saml_controller.py — Routes SSO SAML 2.0 (ADFS / Microsoft Entra ID).

ENDPOINTS (préfixe /api/auth/saml)
    GET  /status    : { enabled: bool } — le frontend affiche le bouton SSO en conséquence
    GET  /metadata  : XML des métadonnées SP (à transmettre à la DSI)
    GET  /login     : SP-initiated SSO — redirige (302) le navigateur vers l'IdP
    POST /acs        : Assertion Consumer Service — reçoit l'assertion signée,
                       crée la session, redirige vers le frontend avec le token

GRACE DEGRADATION
    Si le SSO n'est pas configuré (.env) ou si python3-saml n'est pas installé,
    les routes renvoient 503 avec un message clair — l'app reste fonctionnelle
    en mode local.

EMPLACEMENT MVC
    Couche "controllers" : endpoints HTTP, logique déléguée aux services/providers.
"""

from fastapi import APIRouter, Request, HTTPException, Form
from fastapi.responses import RedirectResponse, Response, HTMLResponse

from app.core.config import settings
from app.auth.saml_settings import build_saml_settings
from app.auth.providers.saml_provider import SamlProvider, SamlNotInstalled, extract_profile
from app.services import auth_service
from app.utils.helpers import request_meta

router = APIRouter(prefix="/api/auth/saml", tags=["SSO SAML"])

# Groupes simulés par rôle (alimentent map_groups_to_role comme une vraie assertion).
_SIM_GROUPS = {
    "HR": ["GRP_RH"],
    "MANAGER": ["GRP_MANAGERS"],
    "COLLAB": ["GRP_COLLABORATEURS"],
}


def _simulation_active() -> bool:
    """La simulation n'est active qu'en dev explicite ET tant que le SSO réel n'est pas configuré."""
    return settings.SAML_SIMULATION and not settings.saml_enabled


def _prepare(request: Request, post_data: dict | None = None) -> dict:
    """Adapte une requête FastAPI au format attendu par python3-saml.

    Honore X-Forwarded-Proto / X-Forwarded-Host (déploiement derrière reverse proxy).
    """
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    hostname = host.split(":")[0]
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
        "enabled": settings.saml_enabled or _simulation_active(),
        "simulation": _simulation_active(),
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
    if _simulation_active():
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
        # Le token transite en query ; le frontend le capte puis nettoie l'URL.
        return RedirectResponse(f"{front}/?sso_token={result['token']}", status_code=302)
    except SamlNotInstalled as e:
        raise HTTPException(status_code=503, detail=str(e))
    except (ValueError, HTTPException):
        # Erreur générique côté client (détail non exposé) — le front affiche un message.
        return RedirectResponse(f"{front}/?sso_error=1", status_code=302)


# =============================================================================
# MODE SIMULATION (DEV UNIQUEMENT) — court-circuite l'IdP réel.
# Permet de tester tout le flux (JIT provisioning, rôle, session, redirection)
# sans Entra ID ni python3-saml. Désactivé en prod et dès que le SSO réel existe.
# =============================================================================

def _require_simulation() -> None:
    if not _simulation_active():
        raise HTTPException(status_code=404, detail="Simulation SSO non disponible.")


@router.get("/simulate", response_class=HTMLResponse)
def simulate_form():
    """Page de choix d'une persona de test (remplace l'écran de login de l'IdP)."""
    _require_simulation()
    return HTMLResponse(_SIMULATION_PAGE)


@router.post("/simulate")
def simulate_submit(
    email: str = Form(...),
    name: str = Form(""),
    role: str = Form("COLLAB"),
):
    """Construit un profil fictif et exécute le VRAI login fédéré, puis redirige."""
    _require_simulation()
    role_up = (role or "COLLAB").strip().upper()
    profile = {
        "email": (email or "").strip(),
        "display_name": (name or "").strip() or (email or "").strip(),
        "groups": _SIM_GROUPS.get(role_up, _SIM_GROUPS["COLLAB"]),
    }
    front = settings.SAML_FRONTEND_REDIRECT
    try:
        result = auth_service.login_from_federated(profile)
        return RedirectResponse(f"{front}/?sso_token={result['token']}", status_code=302)
    except HTTPException:
        return RedirectResponse(f"{front}/?sso_error=1", status_code=302)


_SIMULATION_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SSO BMCI — Simulation</title>
<style>
  *{box-sizing:border-box} body{font-family:system-ui,Segoe UI,Arial,sans-serif;
    background:#f1f5f9;margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
  .card{background:#fff;max-width:440px;width:100%;border-radius:18px;padding:32px;
    box-shadow:0 10px 30px rgba(2,44,34,.08);border:1px solid #e2e8f0}
  h1{color:#065f46;font-size:22px;margin:0 0 4px} .sub{color:#64748b;font-size:13px;margin:0 0 20px}
  .warn{background:#fffbeb;border:1px solid #fde68a;color:#92400e;font-size:12px;
    border-radius:10px;padding:10px 12px;margin-bottom:20px}
  label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;color:#64748b;margin:14px 0 6px}
  input,select{width:100%;padding:11px 12px;border:1px solid #cbd5e1;border-radius:10px;font-size:14px}
  .row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:18px 0 6px}
  .row button{padding:10px;border:1px solid #10b981;background:#ecfdf5;color:#065f46;
    border-radius:10px;font-weight:700;cursor:pointer;font-size:13px}
  .row button:hover{background:#d1fae5}
  .go{width:100%;margin-top:18px;padding:12px;background:#059669;color:#fff;border:0;
    border-radius:10px;font-weight:800;font-size:15px;cursor:pointer}
  .go:hover{background:#047857}
</style></head>
<body>
  <form class="card" method="post" action="/api/auth/saml/simulate">
    <h1>SSO BMCI — Simulation</h1>
    <p class="sub">Écran de test (remplace l'IdP Entra ID). Le reste du flux est réel.</p>
    <div class="warn">⚠️ Mode développement uniquement (SAML_SIMULATION=true).</div>

    <div class="row">
      <button type="button" onclick="fill('rh.sso@bmci.ma','RH Demo','HR')">RH</button>
      <button type="button" onclick="fill('manager.sso@bmci.ma','Manager Demo','MANAGER')">Manager</button>
      <button type="button" onclick="fill('collab.sso@bmci.ma','Collab Demo','COLLAB')">Collab</button>
    </div>

    <label>Email</label>
    <input id="email" name="email" type="email" value="rh.sso@bmci.ma" required>
    <label>Nom affiché</label>
    <input id="name" name="name" type="text" value="RH Demo">
    <label>Rôle (groupe simulé)</label>
    <select id="role" name="role">
      <option value="HR">RH (GRP_RH)</option>
      <option value="MANAGER">Manager (GRP_MANAGERS)</option>
      <option value="COLLAB">Collaborateur (GRP_COLLABORATEURS)</option>
    </select>

    <button class="go" type="submit">Se connecter (simuler l'assertion)</button>
  </form>
  <script>
    function fill(email,name,role){
      document.getElementById('email').value=email;
      document.getElementById('name').value=name;
      document.getElementById('role').value=role;
    }
  </script>
</body></html>"""
