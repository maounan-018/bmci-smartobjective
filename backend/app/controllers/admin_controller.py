#!/usr/bin/env python3
"""
controllers/admin_controller.py — Routes d'administration.

RÔLE
    Expose les endpoints réservés à l'administration (HR/ADMIN), à commencer par
    la consultation du journal d'audit. L'autorisation est déléguée au
    permission_service ; la lecture des logs à l'audit_service.

EMPLACEMENT MVC
    Couche "controllers" : routes/endpoints FastAPI.
"""

from typing import Optional

from fastapi import APIRouter, Depends

from app.controllers.auth_controller import get_current_user
from app.services import audit_service as audit
from app.services.permission_service import require_admin

router = APIRouter(prefix="/api/admin", tags=["Administration"])


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = 100,
    offset: int = 0,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Consultation des logs d'audit — réservé aux administrateurs (HR/ADMIN)."""
    require_admin(current_user)
    logs = audit.fetch_logs(limit=limit, offset=offset, event_type=event_type, user_id=user_id)
    return {"total": len(logs), "logs": logs}
