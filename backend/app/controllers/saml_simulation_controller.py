#!/usr/bin/env python3
"""
controllers/saml_simulation_controller.py — SIMULATION SSO (DÉVELOPPEMENT UNIQUEMENT).

⚠️ FICHIER 100 % JETABLE ⚠️
    Tout le code de simulation SAML est ici, et NULLE PART AILLEURS. Pour le
    retirer définitivement (passage en production) :
      1. Supprimer ce fichier.
      2. Dans app/main.py : retirer les 2 lignes marquées « [SIMULATION] ».
      3. Dans backend/.env : retirer la ligne SAML_SIMULATION (optionnel).
    Aucun autre fichier ne dépend de la simulation.

RÔLE
    Remplace l'écran de login de l'IdP par une page de choix de persona
    (RH / Manager / Collab), puis exécute le VRAI flux fédéré
    (auth_service.login_from_federated). Seule la validation de l'assertion XML
    signée est court-circuitée ; tout le reste est le code de production.

ACTIVATION
    Monté par main UNIQUEMENT si settings.saml_simulation_active
    (SAML_SIMULATION=true ET SSO réel non configuré). En prod ou dès que le SSO
    réel est configuré, ces routes n'existent pas (404).
"""

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse

from app.core.config import settings
from app.services import auth_service
from app.controllers.saml_controller import issue_sso_code

router = APIRouter(prefix="/api/auth/saml", tags=["SSO SAML (simulation)"])

# Groupes simulés par rôle (alimentent map_groups_to_role comme une vraie assertion).
_SIM_GROUPS = {
    "HR": ["GRP_RH"],
    "MANAGER": ["GRP_MANAGERS"],
    "COLLAB": ["GRP_COLLABORATEURS"],
}


def _guard() -> None:
    """Double sécurité : refuse si la simulation n'est pas réellement active."""
    if not settings.saml_simulation_active:
        raise HTTPException(status_code=404, detail="Simulation SSO non disponible.")


@router.get("/simulate", response_class=HTMLResponse)
def simulate_form():
    """Page de choix d'une persona de test (remplace l'écran de login de l'IdP)."""
    _guard()
    return HTMLResponse(_SIMULATION_PAGE)


@router.post("/simulate")
def simulate_submit(
    email: str = Form(...),
    name: str = Form(""),
    role: str = Form("COLLAB"),
):
    """Construit un profil fictif et exécute le VRAI login fédéré, puis redirige."""
    _guard()
    role_up = (role or "COLLAB").strip().upper()
    profile = {
        "email": (email or "").strip(),
        "display_name": (name or "").strip() or (email or "").strip(),
        "groups": _SIM_GROUPS.get(role_up, _SIM_GROUPS["COLLAB"]),
    }
    front = settings.SAML_FRONTEND_REDIRECT
    try:
        # Même flux en 2 temps que l'ACS réel : provision (sans session) -> code.
        user_id = auth_service.provision_federated_user(profile)
        code = issue_sso_code(user_id)
        return RedirectResponse(f"{front}/?sso_code={code}", status_code=302)
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
      <button type="button" onclick="fill('rh.sso@bmci.local','RH Demo','HR')">RH</button>
      <button type="button" onclick="fill('manager.sso@bmci.local','Manager Demo','MANAGER')">Manager</button>
      <button type="button" onclick="fill('collab.sso@bmci.local','Collab Demo','COLLAB')">Collab</button>
    </div>

    <label>Email</label>
    <input id="email" name="email" type="email" value="rh.sso@bmci.local" required>
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
