#!/usr/bin/env python3
"""
core/config.py — Configuration centralisée de l'application.

RÔLE
    Charge le fichier .env (sans dépendance externe) et expose toutes les
    valeurs de configuration via l'objet `settings`. C'est l'unique source
    de configuration : aucun secret ni paramètre ne doit être codé en dur
    ailleurs dans le projet.

EMPLACEMENT MVC
    Couche "core" : configuration et paramètres transverses.
"""

import os


def load_dotenv(path: str = ".env") -> None:
    """
    Charge un fichier .env simple (clé=valeur) dans os.environ.
    N'écrase jamais une variable déjà présente dans l'environnement réel.
    """
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        print(f"[WARNING] Lecture .env impossible: {e}")


class Settings:
    """Paramètres applicatifs lus depuis l'environnement (après load_dotenv)."""

    def __init__(self) -> None:
        # Application
        self.APP_NAME = os.getenv("APP_NAME", "ObjectifSMART-AI")

        # Intelligence artificielle (Ollama)
        self.OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "smart-qwen8")

        # Base de données
        self.DB_PATH = os.getenv("DATABASE_PATH", "objectifsmart.db")

        # Sessions / sécurité
        self.TOKEN_EXPIRY_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "24"))
        self.PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "200000"))
        self.MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.LOGIN_LOCKOUT_MINUTES = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))

        # CORS — JAMAIS "*" en environnement bancaire.
        # Combine a allow_credentials=True (cf. main.py), un wildcard permet
        # CSRF cross-origin : tout site malveillant peut declencher des requetes
        # authentifiees vers l'API depuis le navigateur d'un utilisateur connecte.
        # On exige donc une valeur explicite, sinon le boot echoue.
        _origins_raw = os.getenv("ALLOWED_ORIGINS", "").strip()
        if not _origins_raw or _origins_raw == "*":
            raise RuntimeError(
                "ALLOWED_ORIGINS doit etre defini explicitement dans .env "
                "(ex: ALLOWED_ORIGINS=http://localhost:5173,https://example.com). "
                "Le wildcard \"*\" est interdit car combine a allow_credentials."
            )
        self.ALLOWED_ORIGINS = [o.strip() for o in _origins_raw.split(",") if o.strip()]

        # Limite globale de taille de requete (octets). Protege contre les DoS
        # par upload massif. Valeur en Mo via MAX_REQUEST_SIZE_MB (defaut 20 Mo).
        self.MAX_REQUEST_SIZE_BYTES = int(os.getenv("MAX_REQUEST_SIZE_MB", "20")) * 1024 * 1024

        # Seeding des comptes de demonstration au demarrage (idempotent).
        # Active par defaut pour qu'une copie/clone fonctionne immediatement ;
        # mettre SEED_DEMO_ACCOUNTS=false en production.
        self.SEED_DEMO_ACCOUNTS = os.getenv("SEED_DEMO_ACCOUNTS", "true").strip().lower() in ("1", "true", "yes")
        self.SEED_MANAGER_PASSWORD = os.getenv("SEED_MANAGER_PASSWORD", "")
        self.SEED_HR_PASSWORD = os.getenv("SEED_HR_PASSWORD", "")
        self.SEED_COLLAB_PASSWORD = os.getenv("SEED_COLLAB_PASSWORD", "")

        # --- Authentification : fournisseur d'identite ---
        # local (defaut) | ldap | saml
        self.AUTH_PROVIDER = os.getenv("AUTH_PROVIDER", "local").strip().lower()

        # --- SSO SAML 2.0 (ADFS / Microsoft Entra ID) ---
        # Vide par defaut => SSO desactive (l'app reste en mode local).
        # SP = ce service ; IdP = l'annuaire de la banque.
        self.SAML_SP_ENTITY_ID = os.getenv("SAML_SP_ENTITY_ID", "").strip()
        self.SAML_SP_ACS_URL = os.getenv("SAML_SP_ACS_URL", "").strip()
        self.SAML_SP_SLS_URL = os.getenv("SAML_SP_SLS_URL", "").strip()
        self.SAML_SP_X509_CERT = os.getenv("SAML_SP_X509_CERT", "").strip()
        self.SAML_SP_PRIVATE_KEY = os.getenv("SAML_SP_PRIVATE_KEY", "").strip()
        self.SAML_IDP_ENTITY_ID = os.getenv("SAML_IDP_ENTITY_ID", "").strip()
        self.SAML_IDP_SSO_URL = os.getenv("SAML_IDP_SSO_URL", "").strip()
        self.SAML_IDP_SLO_URL = os.getenv("SAML_IDP_SLO_URL", "").strip()
        self.SAML_IDP_X509_CERT = os.getenv("SAML_IDP_X509_CERT", "").strip()
        self.SAML_STRICT = os.getenv("SAML_STRICT", "true").strip().lower() in ("1", "true", "yes")
        # Apres login SSO, on renvoie le navigateur vers cette base d'URL frontend.
        self.SAML_FRONTEND_REDIRECT = os.getenv("SAML_FRONTEND_REDIRECT", "http://localhost:3000").strip().rstrip("/")
        # Noms de claims (valeurs Microsoft par defaut ; vide => fallback intelligent).
        self.SAML_ATTR_EMAIL = os.getenv("SAML_ATTR_EMAIL", "").strip()
        self.SAML_ATTR_NAME = os.getenv("SAML_ATTR_NAME", "").strip()
        self.SAML_ATTR_GROUPS = os.getenv(
            "SAML_ATTR_GROUPS",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups",
        ).strip()
        self.SAML_DEFAULT_ROLE = os.getenv("SAML_DEFAULT_ROLE", "COLLAB").strip().upper()

    @property
    def saml_sp_ready(self) -> bool:
        """Vrai si le SP est configure (suffisant pour servir les metadonnees)."""
        return bool(self.SAML_SP_ENTITY_ID and self.SAML_SP_ACS_URL)

    @property
    def saml_idp_ready(self) -> bool:
        """Vrai si l'IdP est configure (entityId + SSO URL + certificat)."""
        return bool(self.SAML_IDP_ENTITY_ID and self.SAML_IDP_SSO_URL and self.SAML_IDP_X509_CERT)

    @property
    def saml_enabled(self) -> bool:
        """Vrai si le flux SSO complet est utilisable (SP + IdP configures)."""
        return self.saml_sp_ready and self.saml_idp_ready


# Chargement du .env puis instanciation unique partagée dans toute l'application
load_dotenv()
settings = Settings()
