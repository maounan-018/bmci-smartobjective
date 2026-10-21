#!/usr/bin/env python3
"""
tests/test_saml.py — Tests du SSO SAML SANS dépendance native ni IdP réel.

On vérifie :
  - la dégradation propre quand le SSO n'est pas configuré (503 / status=false) ;
  - le JIT provisioning de auth_service.login_from_federated (création + rôle) ;
  - le mapping des groupes -> rôle (dont ADMIN ramené à HR) ;
  - l'extraction de profil depuis une assertion (claims Microsoft + fallback NameID).

Aucun de ces tests n'importe python3-saml : ils exercent la logique pure.
"""

import pytest
from app.auth.identity_provider import map_groups_to_role
from app.auth.providers.saml_provider import extract_profile
from app.database.session import db_session
from app.repositories import user_repository
from app.services import auth_service
from fastapi import HTTPException

# ----------------------- Dégradation propre (non configuré) -----------------------


def test_saml_status_disabled_by_default(client):
    """En l'absence de config SAML, /status indique enabled=false (et pas de simulation)."""
    resp = client.get("/api/auth/saml/status")
    assert resp.status_code == 200
    assert resp.json() == {"enabled": False, "simulation": False}


def test_saml_login_returns_503_when_not_configured(client):
    resp = client.get("/api/auth/saml/login", follow_redirects=False)
    assert resp.status_code == 503


def test_saml_acs_returns_503_when_not_configured(client):
    resp = client.post("/api/auth/saml/acs", data={"SAMLResponse": "x"}, follow_redirects=False)
    assert resp.status_code == 503


def test_saml_metadata_returns_503_when_not_configured(client):
    resp = client.get("/api/auth/saml/metadata")
    assert resp.status_code == 503


def test_sso_code_exchange_single_use(client, make_user):
    """Un code SSO s'échange une seule fois (la session est créée à l'échange),
    puis devient invalide. Le code mappe vers un utilisateur, jamais vers un token."""
    make_user(user_id="u-sso-x", email="ssox@bmci.ma", role="COLLAB")
    from app.controllers.saml_controller import issue_sso_code

    code = issue_sso_code("u-sso-x")

    r1 = client.post("/api/auth/saml/exchange", json={"code": code})
    assert r1.status_code == 200
    token = r1.json()["token"]
    # Le token renvoyé ouvre bien une session valide.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "ssox@bmci.ma"

    # Usage unique : un 2e échange du même code échoue.
    r2 = client.post("/api/auth/saml/exchange", json={"code": code})
    assert r2.status_code == 400


def test_sso_code_no_token_stored_in_db(client, make_user):
    """La table sso_codes ne contient JAMAIS de token de session : seulement le
    hash du code et un user_id (défense en profondeur si la base fuite)."""
    make_user(user_id="u-sso-y", email="ssoy@bmci.ma", role="COLLAB")
    from app.controllers.saml_controller import issue_sso_code
    from app.database.session import db_session
    from app.models.sso_code import SsoCode

    code = issue_sso_code("u-sso-y")
    with db_session() as db:
        row = db.query(SsoCode).one()
        # Ni le code en clair, ni un token ne sont stockés.
        assert row.code_hash != code
        assert row.user_id == "u-sso-y"
        assert not hasattr(row, "token")


def test_sso_code_exchange_invalid(client):
    """Un code SSO inconnu est refusé."""
    r = client.post("/api/auth/saml/exchange", json={"code": "inexistant"})
    assert r.status_code == 400


def test_saml_simulation_disabled_by_default(client):
    """Sans SAML_SIMULATION=true, les routes de simulation n'existent pas (404)."""
    assert client.get("/api/auth/saml/simulate", follow_redirects=False).status_code == 404
    assert (
        client.post(
            "/api/auth/saml/simulate",
            data={"email": "x@bmci.ma", "role": "HR"},
            follow_redirects=False,
        ).status_code
        == 404
    )


# ----------------------- JIT provisioning (login fédéré) -----------------------


def test_login_from_federated_creates_user_with_mapped_role(client):
    """Un email inconnu est provisionné avec le rôle déduit des groupes."""
    result = auth_service.login_from_federated(
        {
            "email": "ssomgr@bmci.ma",
            "display_name": "SSO Manager",
            "groups": ["GRP_MANAGERS"],
        }
    )
    assert result["success"] is True
    assert result["user"]["role"] == "MANAGER"
    assert result["user"]["email"] == "ssomgr@bmci.ma"

    # Le token créé fonctionne sur un endpoint protégé.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {result['token']}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "ssomgr@bmci.ma"


def test_login_from_federated_admin_group_clamped_to_hr(client):
    """ADMIN (interdit en base) est ramené à HR."""
    result = auth_service.login_from_federated(
        {
            "email": "ssoadmin@bmci.ma",
            "display_name": "SSO Admin",
            "groups": ["GRP_ADMIN_OBJECTIFS"],
        }
    )
    assert result["user"]["role"] == "HR"


def test_login_from_federated_unknown_group_defaults_collab(client):
    result = auth_service.login_from_federated(
        {
            "email": "ssouser@bmci.ma",
            "display_name": "SSO User",
            "groups": ["GROUPE_INCONNU"],
        }
    )
    assert result["user"]["role"] == "COLLAB"


def test_login_from_federated_existing_user_no_duplicate(client, make_user):
    """Un email déjà connu réutilise le compte (pas de doublon, rôle conservé)."""
    make_user(user_id="u-exist", email="exist@bmci.ma", role="COLLAB")
    result = auth_service.login_from_federated(
        {
            "email": "exist@bmci.ma",
            "display_name": "Existant",
            "groups": ["GRP_MANAGERS"],  # ne doit PAS écraser le rôle existant
        }
    )
    assert result["user"]["id"] == "u-exist"
    assert result["user"]["role"] == "COLLAB"
    with db_session() as db:
        assert len(user_repository.get_all_ids(db)) == 1


def test_login_from_federated_missing_email_raises(client):
    with pytest.raises(HTTPException) as exc:
        auth_service.login_from_federated({"email": "", "groups": []})
    assert exc.value.status_code == 400


# ----------------------- Mapping & extraction -----------------------


def test_map_groups_to_role_priority():
    assert map_groups_to_role(["GRP_COLLABORATEURS", "GRP_RH"]) == "HR"
    assert map_groups_to_role(["GRP_MANAGERS"]) == "MANAGER"
    assert map_groups_to_role([]) == "COLLAB"


def test_extract_profile_email_fallback_to_nameid():
    """Sans claim email, on retombe sur le NameID (cas fréquent Entra/ADFS)."""
    profile = extract_profile({"nameid": "jean@bmci.ma", "attributes": {}})
    assert profile["email"] == "jean@bmci.ma"


def test_extract_profile_reads_microsoft_email_and_groups_claims():
    raw = {
        "nameid": "ignored@bmci.ma",
        "attributes": {
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": ["alice@bmci.ma"],
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": ["GRP_RH"],
        },
    }
    profile = extract_profile(raw)
    assert profile["email"] == "alice@bmci.ma"
    assert profile["groups"] == ["GRP_RH"]
