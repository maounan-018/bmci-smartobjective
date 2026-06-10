#!/usr/bin/env python3
"""
auth/saml_settings.py — Construit la configuration SAML attendue par python3-saml.

RÔLE
    Traduit les variables .env (settings) en dictionnaire de configuration
    OneLogin (SP + IdP + sécurité). Aucune dépendance native ici : ce module
    se contente d'assembler un dict, il n'importe PAS python3-saml.

SÉCURITÉ (par défaut, durci pour la banque)
    - wantAssertionsSigned = True  : on EXIGE des assertions signées par l'IdP.
    - signatureAlgorithm = RSA-SHA256, digest = SHA256 (pas de SHA-1).
    - strict = True : tout écart (audience, dates, signature) => rejet.

EMPLACEMENT MVC
    Couche "auth" : préparation de l'authentification fédérée.
"""

from app.core.config import settings

_BINDING_POST = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
_BINDING_REDIRECT = "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
_NAMEID_EMAIL = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"


def build_saml_settings() -> dict:
    """Assemble le dict de configuration python3-saml à partir du .env."""
    s = settings

    sp = {
        "entityId": s.SAML_SP_ENTITY_ID,
        "assertionConsumerService": {"url": s.SAML_SP_ACS_URL, "binding": _BINDING_POST},
        "NameIDFormat": _NAMEID_EMAIL,
        "x509cert": s.SAML_SP_X509_CERT,
        "privateKey": s.SAML_SP_PRIVATE_KEY,
    }
    if s.SAML_SP_SLS_URL:
        sp["singleLogoutService"] = {"url": s.SAML_SP_SLS_URL, "binding": _BINDING_REDIRECT}

    idp = {
        "entityId": s.SAML_IDP_ENTITY_ID,
        "singleSignOnService": {"url": s.SAML_IDP_SSO_URL, "binding": _BINDING_REDIRECT},
        "x509cert": s.SAML_IDP_X509_CERT,
    }
    if s.SAML_IDP_SLO_URL:
        idp["singleLogoutService"] = {"url": s.SAML_IDP_SLO_URL, "binding": _BINDING_REDIRECT}

    return {
        "strict": s.SAML_STRICT,
        "debug": False,
        "sp": sp,
        "idp": idp,
        "security": {
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
            "wantNameId": True,
            "requestedAuthnContext": False,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            # ADFS/Entra : on signe nos requêtes seulement si une clé SP est fournie.
            "authnRequestsSigned": bool(s.SAML_SP_PRIVATE_KEY),
            "logoutRequestSigned": bool(s.SAML_SP_PRIVATE_KEY),
            "logoutResponseSigned": bool(s.SAML_SP_PRIVATE_KEY),
        },
    }
