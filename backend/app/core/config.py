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


# Chargement du .env puis instanciation unique partagée dans toute l'application
load_dotenv()
settings = Settings()
