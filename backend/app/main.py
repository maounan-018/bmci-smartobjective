#!/usr/bin/env python3
"""
main.py — Assemblage de l'application FastAPI (architecture MVC).

RÔLE
    Point de composition : crée l'app, applique le CORS, initialise la base et la
    table d'audit, puis monte les routeurs (controllers). C'est l'équivalent
    structuré de l'ancien server.py monolithique.

ÉTAT DE LA MIGRATION MVC
    - Domaine "auth" : entièrement migré (controllers/auth_controller.py).
    - Couches transverses (core, database, models, services, auth-provider) : en place.
    - Domaines métier (objectives, manager, hr, ai) : à monter ici au fur et à
      mesure de leur extraction depuis l'ancien server.py, sur le MÊME modèle que
      auth_controller.py (un router par domaine, logique dans les services).

EMPLACEMENT MVC
    Racine applicative : composition et démarrage.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middlewares.request_size import LimitRequestSizeMiddleware
from app.database.init_db import init_db
from app.controllers.auth_controller import router as auth_router
from app.controllers.admin_controller import router as admin_router
from app.controllers.objective_controller import router as objective_router
from app.controllers.manager_controller import router as manager_router
from app.controllers.hr_controller import router as hr_router
from app.controllers.ai_controller import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Au démarrage : créer les tables ORM manquantes (idempotent)."""
    init_db()
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
    app.include_router(admin_router)
    app.include_router(objective_router)
    app.include_router(manager_router)
    app.include_router(hr_router)
    app.include_router(ai_router)

    @app.get("/health")
    def health():
        """Sonde de disponibilité."""
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
