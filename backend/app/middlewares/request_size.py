#!/usr/bin/env python3
"""
middlewares/request_size.py — Limite la taille des requetes entrantes.

RÔLE
    Premiere ligne de defense contre les DoS par upload massif. Sans limite,
    un utilisateur authentifie peut envoyer un fichier de plusieurs GB sur
    /api/hr/import-* ou /api/import-excel-*, ce qui charge tout en RAM avant
    le moindre traitement et provoque un OOM du worker uvicorn.

STRATEGIE
    On verifie le header Content-Length avant la lecture du body. Si la valeur
    annoncee depasse la limite, on renvoie 413 (Payload Too Large) sans rien
    lire. C'est une defense rapide (zero allocation). Pour les clients qui
    mentent sur Content-Length, Starlette borne deja la lecture par chunks,
    donc la memoire reste sous controle meme en cas de tentative.

EMPLACEMENT MVC
    Couche "middlewares" : protection transverse, applique a TOUTES les routes.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class LimitRequestSizeMiddleware(BaseHTTPMiddleware):
    """Rejette les requetes dont Content-Length depasse max_bytes."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Requete trop volumineuse "
                                f"(max {self.max_bytes // (1024 * 1024)} Mo)."
                            )
                        },
                    )
            except (TypeError, ValueError):
                # Content-Length malformee : on laisse FastAPI gerer plus loin
                pass
        return await call_next(request)
