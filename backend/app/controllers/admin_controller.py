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
from app.schemas.admin_schema import (
    AdminUserCreate, AdminUserUpdate, AdminPasswordReset, AdminActiveUpdate,
)
from app.services import audit_service as audit
from app.services import user_service
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


# ============= GESTION DES COMPTES (HR/ADMIN) =============

@router.get("/users")
def list_users(current_user: dict = Depends(get_current_user)):
    """Liste tous les comptes (administration)."""
    return user_service.admin_list_users(current_user)


@router.post("/users")
def create_user(request: AdminUserCreate, current_user: dict = Depends(get_current_user)):
    """Crée un compte."""
    return user_service.admin_create_user(current_user, request)


@router.put("/users/{user_id}")
def update_user(user_id: str, request: AdminUserUpdate, current_user: dict = Depends(get_current_user)):
    """Met à jour un compte (nom, rôle, manager, entité)."""
    return user_service.admin_update_user(current_user, user_id, request)


@router.patch("/users/{user_id}/active")
def set_user_active(user_id: str, request: AdminActiveUpdate, current_user: dict = Depends(get_current_user)):
    """Active ou désactive un compte."""
    return user_service.admin_set_user_active(current_user, user_id, request.active)


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: str, request: AdminPasswordReset, current_user: dict = Depends(get_current_user)):
    """Réinitialise le mot de passe d'un compte."""
    return user_service.admin_reset_password(current_user, user_id, request.password)


@router.delete("/users/{user_id}")
def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Supprime définitivement un compte (cascade objectifs/sessions)."""
    return user_service.admin_delete_user(current_user, user_id)
