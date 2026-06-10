#!/usr/bin/env python3
"""
auth/providers/saml_provider.py — Fournisseur d'identité SAML 2.0 (ADFS / Entra ID).

RÔLE
    Encapsule python3-saml (OneLogin). Contrairement aux providers Local/LDAP,
    SAML n'utilise PAS authenticate(email, password) : l'IdP authentifie
    l'utilisateur et renvoie une assertion signée. Ce provider sait donc :
      - build_login_url()   : construire la requête d'authentification (redirect IdP)
      - process_response()  : vérifier l'assertion reçue sur l'ACS
      - metadata()          : produire les métadonnées SP (à fournir à la DSI)

IMPORT PARESSEUX
    python3-saml dépend de xmlsec (binaire natif). On ne l'importe QUE lors d'un
    appel réel, pour que l'application démarre normalement en mode local même si
    la librairie n'est pas installée.

EMPLACEMENT MVC
    Couche "auth" : authentification fédérée.
"""

from typing import Optional

from app.core.config import settings


class SamlNotInstalled(RuntimeError):
    """Levée quand python3-saml n'est pas disponible dans l'environnement."""


class SamlProvider:
    """Adaptateur autour de OneLogin python3-saml (import paresseux)."""

    def __init__(self, settings_dict: dict):
        self._settings = settings_dict

    @staticmethod
    def _load():
        """Importe python3-saml à la demande ; message clair si absent."""
        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            from onelogin.saml2.settings import OneLogin_Saml2_Settings
            return OneLogin_Saml2_Auth, OneLogin_Saml2_Settings
        except ImportError as e:  # pragma: no cover (dépend de l'env)
            raise SamlNotInstalled(
                "python3-saml n'est pas installé. "
                "Exécutez : pip install -r requirements-saml.txt"
            ) from e

    def build_login_url(self, req: dict, return_to: Optional[str] = None) -> str:
        """Construit l'URL de redirection vers l'IdP (SP-initiated SSO)."""
        Auth, _ = self._load()
        auth = Auth(req, old_settings=self._settings)
        return auth.login(return_to=return_to)

    def process_response(self, req: dict) -> dict:
        """Vérifie l'assertion reçue (signature, audience, dates) et renvoie le brut."""
        Auth, _ = self._load()
        auth = Auth(req, old_settings=self._settings)
        auth.process_response()

        errors = auth.get_errors()
        if errors:
            reason = auth.get_last_error_reason() or ""
            raise ValueError(f"Assertion SAML invalide: {', '.join(errors)} {reason}".strip())
        if not auth.is_authenticated():
            raise ValueError("SAML: utilisateur non authentifié.")

        return {
            "nameid": auth.get_nameid(),
            "attributes": auth.get_attributes() or {},
            "session_index": auth.get_session_index(),
        }

    def metadata(self) -> str:
        """Génère et valide les métadonnées SP (XML) à transmettre à la DSI."""
        _, Settings = self._load()
        saml_settings = Settings(self._settings, sp_validation_only=True)
        meta = saml_settings.get_sp_metadata()
        errors = saml_settings.validate_metadata(meta)
        if errors:
            raise ValueError(f"Métadonnées SP invalides: {', '.join(errors)}")
        return meta.decode("utf-8") if isinstance(meta, bytes) else meta


def _first(attributes: dict, key: str) -> Optional[str]:
    """Première valeur d'un claim multi-valué (python3-saml renvoie des listes)."""
    if not key:
        return None
    val = attributes.get(key)
    if isinstance(val, list) and val:
        return val[0]
    if isinstance(val, str):
        return val
    return None


# Claims Microsoft (ADFS / Entra ID) couramment rencontrés, en fallback.
_EMAIL_CLAIMS = (
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    "emailaddress", "email", "mail", "upn",
)
_NAME_CLAIMS = (
    "http://schemas.microsoft.com/identity/claims/displayname",
    "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
    "displayName", "name", "cn",
)


def extract_profile(raw: dict) -> dict:
    """
    Normalise l'assertion en profil applicatif : {email, display_name, groups}.

    Stratégie email : claim configuré -> claims Microsoft connus -> NameID.
    Stratégie groupes : claim configuré -> 'groups' -> 'memberOf'.
    """
    attrs = raw.get("attributes") or {}
    nameid = raw.get("nameid") or ""

    email = _first(attrs, settings.SAML_ATTR_EMAIL)
    if not email:
        for k in _EMAIL_CLAIMS:
            email = _first(attrs, k)
            if email:
                break
    if not email:
        email = nameid  # sous Entra/ADFS, le NameID est souvent l'email/UPN

    name = _first(attrs, settings.SAML_ATTR_NAME)
    if not name:
        for k in _NAME_CLAIMS:
            name = _first(attrs, k)
            if name:
                break

    groups = attrs.get(settings.SAML_ATTR_GROUPS) or attrs.get("groups") or attrs.get("memberOf") or []
    if isinstance(groups, str):
        groups = [groups]

    return {
        "email": (email or "").strip(),
        "display_name": (name or email or "").strip(),
        "groups": list(groups),
    }
