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
import logging


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
        logging.getLogger(__name__).warning("Lecture .env impossible: %s", e)


class Settings:
    """Paramètres applicatifs lus depuis l'environnement (après load_dotenv)."""

    def __init__(self) -> None:
        # Application
        self.APP_NAME = os.getenv("APP_NAME", "ObjectifSMART-AI")
        # Niveau de log applicatif : DEBUG | INFO | WARNING | ERROR. En prod -> INFO
        # (masque les logs DEBUG, donc aucune donnee RH dans les journaux).
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

        # Intelligence artificielle (Ollama)
        self.OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "smart-qwen8")
        # Modele du Coach IA conversationnel (chat). Defaut = qwen3:8b (modele de
        # base : contexte large ~40k tokens, ton naturel) plutot que smart-qwen8,
        # specialise pour des sorties JSON SMART et limite a 4096 tokens (l'historique
        # du chat y serait tronque silencieusement).
        self.OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen3:8b")
        # Nombre d'essais d'appel au modele : il renvoie parfois {} (vide) ou du
        # texte non parsable ; un reessai evite l'analyse degradee "tout faux, sans
        # reformulation". 1 = aucun reessai (cf. ai_service.call_ollama).
        self.AI_MAX_ATTEMPTS = int(os.getenv("AI_MAX_ATTEMPTS", "2"))

        # RAG (assistant « base de connaissances ») — embeddings 100% locaux via
        # Ollama, stockes et cherches DANS SQLite grace a l'extension sqlite-vec
        # (aucune base vectorielle externe : tout reste sur l'infra => conforme CNDP).
        self.OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")
        # Dimension des vecteurs du modele d'embedding (fixe le schema de la table
        # vec0). Doit correspondre au modele ci-dessus : bge-m3 = 1024.
        self.RAG_EMBEDDING_DIM = int(os.getenv("RAG_EMBEDDING_DIM", "1024"))
        # Seuil de pertinence du RAG : au-dela de cette distance (L2, bge-m3) un
        # passage est juge hors-sujet et ecarte -> le Coach repond SANS contexte
        # plutot que d'injecter un passage non pertinent qui le ferait divaguer.
        # Calibre sur bge-m3 : on-topic <= ~24, hors-sujet >= ~30 ; 28 = marge sure.
        self.RAG_MAX_DISTANCE = float(os.getenv("RAG_MAX_DISTANCE", "28"))

        # KPI RH (seuils du tableau de bord, réglables sans toucher au code).
        self.KPI_SMART_THRESHOLD = int(os.getenv("KPI_SMART_THRESHOLD", "80"))        # objectif "conforme"
        self.KPI_ALIGNMENT_STRONG = int(os.getenv("KPI_ALIGNMENT_STRONG", "75"))      # alignement "fort"
        self.KPI_AXIS_OVERCONCENTRATION = float(os.getenv("KPI_AXIS_OVERCONCENTRATION", "40"))  # % max sur un axe
        # Confiance minimale de l'IA (0.0-1.0) en deçà de laquelle l'analyse est
        # signalée pour RELECTURE HUMAINE. L'IA reste une aide à la décision : quand
        # elle est elle-même incertaine (modèle indécis, défaut 0.5, ou échec 0.0),
        # un humain doit valider. 0.6 capture incertitude réelle + défauts + échecs.
        self.KPI_AI_CONFIDENCE_MIN = float(os.getenv("KPI_AI_CONFIDENCE_MIN", "0.6"))

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

        # Rate limiting des appels IA (anti-saturation d'Ollama, traite en serie).
        # Au plus AI_RATE_LIMIT_MAX analyses par AI_RATE_LIMIT_WINDOW_SECONDS et par
        # utilisateur. Etat en base (table ai_calls) => multi-worker, cf.
        # services/ai_rate_limit_service.
        self.AI_RATE_LIMIT_MAX = int(os.getenv("AI_RATE_LIMIT_MAX", "10"))
        self.AI_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AI_RATE_LIMIT_WINDOW_SECONDS", "60"))

        # Seeding des comptes de demonstration au demarrage (idempotent).
        # Active par defaut pour qu'une copie/clone fonctionne immediatement ;
        # mettre SEED_DEMO_ACCOUNTS=false en production.
        self.SEED_DEMO_ACCOUNTS = os.getenv("SEED_DEMO_ACCOUNTS", "true").strip().lower() in ("1", "true", "yes")
        self.SEED_MANAGER_PASSWORD = os.getenv("SEED_MANAGER_PASSWORD", "")
        self.SEED_HR_PASSWORD = os.getenv("SEED_HR_PASSWORD", "")
        self.SEED_COLLAB_PASSWORD = os.getenv("SEED_COLLAB_PASSWORD", "")

        # --- Authentification : fournisseur d'identite ---
        # local (defaut). Le SSO SAML s'active des que SP + IdP sont configures.
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
        # Mode SIMULATION (DEV UNIQUEMENT) : court-circuite l'IdP réel pour tester
        # le flux SSO de bout en bout sans Entra ID ni python3-saml. JAMAIS en prod.
        # Ignoré automatiquement dès que le SSO réel (SP+IdP) est configuré.
        self.SAML_SIMULATION = os.getenv("SAML_SIMULATION", "false").strip().lower() in ("1", "true", "yes")

        # Environnement de déploiement : development (defaut) | production.
        # En production, la simulation SSO est refusée (garde-fou anti-bypass).
        self.ENV = os.getenv("ENV", "development").strip().lower()

        # Connexion locale (email/mot de passe). "auto" (defaut) = activée seulement
        # si le SSO réel n'est pas configuré ; "true"/"false" pour forcer.
        # En SSO réel, on la coupe pour éviter une porte dérobée via comptes seedés.
        self.LOCAL_AUTH_ENABLED = os.getenv("LOCAL_AUTH_ENABLED", "auto").strip().lower()

        # Filtre d'autorisation SSO (optionnel) : si défini, seuls les utilisateurs
        # appartenant à au moins un de ces groupes peuvent se connecter en SSO.
        # Vide (defaut) = aucun filtre (tout employé authentifié est accepté).
        self.SAML_ALLOWED_GROUPS = [
            g.strip() for g in os.getenv("SAML_ALLOWED_GROUPS", "").split(",") if g.strip()
        ]

    @property
    def is_production(self) -> bool:
        return self.ENV in ("production", "prod")

    @property
    def local_auth_enabled(self) -> bool:
        """Connexion locale autorisée ? Coupée par défaut dès que le SSO réel est actif."""
        if self.LOCAL_AUTH_ENABLED in ("true", "1", "yes"):
            return True
        if self.LOCAL_AUTH_ENABLED in ("false", "0", "no"):
            return False
        return not self.saml_enabled  # "auto"

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

    @property
    def saml_simulation_active(self) -> bool:
        """Simulation active : flag dev explicite, SSO reel non configure, ET hors prod.
        En production la simulation est TOUJOURS refusee (anti-bypass d'authentification)."""
        return self.SAML_SIMULATION and not self.saml_enabled and not self.is_production

    @property
    def auth_mode(self) -> str:
        """Mode d'authentification effectif (pour le log de demarrage)."""
        if self.saml_enabled:
            return "SSO SAML (reel)"
        if self.saml_simulation_active:
            return "SSO SAML (SIMULATION - DEV)"
        return "local"


# Chargement de la configuration. .env.local (secrets locaux, ignore par git)
# est lu EN PREMIER pour etre prioritaire : load_dotenv n'ecrase jamais une cle
# deja presente. .env fournit ensuite la config par defaut versionnee.
load_dotenv(".env.local")
load_dotenv(".env")
settings = Settings()
