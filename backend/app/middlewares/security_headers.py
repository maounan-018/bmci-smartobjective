#!/usr/bin/env python3
"""
middlewares/security_headers.py — En-têtes de sécurité HTTP sur toutes les réponses.

RÔLE
    Défense en profondeur côté navigateur :
      - X-Content-Type-Options: nosniff   -> empêche le MIME-sniffing
      - X-Frame-Options: DENY              -> anti-clickjacking (API jamais en iframe)
      - Referrer-Policy                    -> ne fuite pas l'URL complète en cross-origin
      - Strict-Transport-Security (HSTS)   -> force HTTPS (ignoré en clair, inoffensif)
      - X-Permitted-Cross-Domain-Policies  -> bloque les politiques Flash/PDF héritées

    On utilise setdefault : un header déjà positionné par une route n'est pas écrasé.

EMPLACEMENT MVC
    Couche "middlewares" : protection transverse, appliquée à TOUTES les routes.
"""

from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Ajoute les en-têtes de sécurité standards à chaque réponse."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        return response
