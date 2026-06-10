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

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middlewares.request_size import LimitRequestSizeMiddleware
from app.database.init_db import init_db
from app.database.seed import seed_demo_accounts
from app.controllers.auth_controller import router as auth_router
from app.controllers.saml_controller import router as saml_router
from app.controllers.admin_controller import router as admin_router
from app.controllers.objective_controller import router as objective_router
from app.controllers.manager_controller import router as manager_router
from app.controllers.hr_controller import router as hr_router
from app.controllers.ai_controller import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Au démarrage : créer les tables ORM, semer les comptes démo, logguer le mode d'auth."""
    init_db()
    seed_demo_accounts()
    # Bannière de démarrage : rend le mode d'authentification visible (et signale
    # bruyamment la simulation pour éviter tout déploiement accidentel en prod).
    if settings.saml_simulation_active:
        print("=" * 64)
        print("  [AUTH] Mode = SSO SAML *** SIMULATION (DEV) *** — NE PAS UTILISER EN PROD")
        print("=" * 64)
    else:
        print(f"  [AUTH] Mode = {settings.auth_mode}")
    yield


def create_app() -> FastAPI:
    """Fabrique l'application FastAPI configurée (pattern factory)."""
    app = FastAPI(title=settings.APP_NAME, version="3.0.0", lifespan=lifespan)

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

    # [SIMULATION] Routes de simulation SSO — montées UNIQUEMENT en dev (jetable).
    if settings.saml_simulation_active:
        from app.controllers.saml_simulation_controller import router as saml_sim_router
        app.include_router(saml_sim_router)

    @app.get("/health")
    def health():
        """Sonde de disponibilité."""
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
