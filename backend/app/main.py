#!/usr/bin/env python3
"""
main.py — Assemblage de l'application FastAPI (architecture MVC).

RÔLE
    Point de composition : crée l'app, applique le CORS, initialise la base et la
    table d'audit, puis monte les routeurs (controllers). C'est l'équivalent
    structuré de l'ancien server.py monolithique.

ÉTAT DE LA MIGRATION MVC
    Migration terminée : tous les domaines (auth, admin, objectives, manager, hr,
    ai) sont extraits en routers dédiés et montés ci-dessous. Chaque router délègue
    sa logique aux services ; aucune logique métier ne subsiste dans ce fichier.

EMPLACEMENT MVC
    Racine applicative : composition et démarrage.
"""

import logging
from contextlib import asynccontextmanager

import requests
from app.controllers.admin_controller import router as admin_router
from app.controllers.ai_controller import router as ai_router
from app.controllers.auth_controller import router as auth_router
from app.controllers.hr_controller import router as hr_router
from app.controllers.manager_controller import router as manager_router
from app.controllers.objective_controller import router as objective_router
from app.controllers.rag_controller import router as rag_router
from app.controllers.saml_controller import router as saml_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.database.init_db import init_db
from app.database.seed import seed_demo_accounts
from app.database.session import db_session
from app.middlewares.request_size import LimitRequestSizeMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Au démarrage : créer les tables ORM, semer les comptes démo, logguer le mode d'auth."""
    init_db()
    seed_demo_accounts()
    # Bannière de démarrage : rend le mode d'authentification visible (et signale
    # bruyamment la simulation pour éviter tout déploiement accidentel en prod).
    if settings.saml_simulation_active:
        logger.warning("=" * 64)
        logger.warning("[AUTH] Mode = SSO SAML *** SIMULATION (DEV) *** — NE PAS UTILISER EN PROD")
        logger.warning("=" * 64)
    else:
        logger.info("[AUTH] Mode = %s", settings.auth_mode)
    yield


def create_app() -> FastAPI:
    """Fabrique l'application FastAPI configurée (pattern factory)."""
    setup_logging()
    app = FastAPI(title=settings.APP_NAME, version="3.0.0", lifespan=lifespan)

    # En-têtes de sécurité sur toutes les réponses (defense en profondeur).
    app.add_middleware(SecurityHeadersMiddleware)

    # Protection DoS : rejette les requetes > MAX_REQUEST_SIZE_MB
    # (defaut 20 Mo, configurable via .env). A appliquer AVANT CORS pour
    # qu'une requete oversize ne consomme aucun cycle CPU autre que le check.
    app.add_middleware(
        LimitRequestSizeMiddleware,
        max_bytes=settings.MAX_REQUEST_SIZE_BYTES,
    )

    # CORS restreint via .env (jamais "*" en production bancaire)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Montage des routeurs (un par domaine métier)
    app.include_router(auth_router)
    app.include_router(saml_router)
    app.include_router(admin_router)
    app.include_router(objective_router)
    app.include_router(manager_router)
    app.include_router(hr_router)
    app.include_router(ai_router)
    app.include_router(rag_router)

    # [SIMULATION] Routes de simulation SSO — montées UNIQUEMENT en dev (jetable).
    if settings.saml_simulation_active:
        from app.controllers.saml_simulation_controller import router as saml_sim_router

        app.include_router(saml_sim_router)

    @app.get("/health")
    def health():
        """Sonde de LIVENESS : le process répond (ne teste pas les dépendances)."""
        return {"status": "ok", "app": settings.APP_NAME}

    @app.get("/health/ready")
    def health_ready(response: Response):
        """Sonde de READINESS : l'app peut-elle réellement servir ?

        - Base de données : dépendance **critique** -> HTTP 503 si KO.
        - Ollama (modèle IA) : dépendance **souple** ; si indisponible, l'app reste
          utilisable hors analyses -> statut 'degraded' mais HTTP 200 (ne pas sortir
          toute l'app de la rotation du load balancer pour une panne IA).
        """
        checks: dict[str, str] = {}

        db_ok = True
        try:
            with db_session() as db:
                db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception:
            db_ok = False
            checks["database"] = "unreachable"

        ollama_ok = True
        try:
            base = settings.OLLAMA_URL.split("/api/")[0]
            r = requests.get(f"{base}/api/tags", timeout=2)
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
            if any(
                n == settings.OLLAMA_MODEL or n.startswith(f"{settings.OLLAMA_MODEL}:")
                for n in models
            ):
                checks["ollama"] = "ok"
            else:
                ollama_ok = False
                checks["ollama"] = f"modele '{settings.OLLAMA_MODEL}' absent"
        except Exception:
            ollama_ok = False
            checks["ollama"] = "unreachable"

        if not db_ok:
            response.status_code = 503
            status = "not_ready"
        elif not ollama_ok:
            status = "degraded"
        else:
            status = "ready"
        return {"status": status, "checks": checks, "app": settings.APP_NAME}

    return app


app = create_app()
