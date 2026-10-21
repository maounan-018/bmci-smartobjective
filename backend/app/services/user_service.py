#!/usr/bin/env python3
"""
services/user_service.py — Logique métier liée aux utilisateurs.

RÔLE
    Expose les opérations de lecture sur les utilisateurs nécessaires aux
    controllers : membres d'équipe selon le rôle. Toute la persistance passe
    par user_repository.

EMPLACEMENT MVC
    Couche "services" : logique métier.
"""

import secrets

from app.core import security
from app.core.emails import is_valid_bnp_email
from app.database.session import db_session
from app.repositories import session_repository, user_repository
from app.services.permission_service import require_super_admin
from fastapi import HTTPException


def get_team_members(current_user: dict) -> dict:
    """
    Membres d'équipe selon le rôle (réservé MANAGER/HR) :
      - MANAGER : uniquement son équipe
      - HR      : vue globale (analytics)
    """
    if current_user["role"] == "COLLAB":
        raise HTTPException(status_code=403, detail="Accès réservé aux managers et RH.")

    with db_session() as db:
        if current_user["role"] == "MANAGER":
            members = user_repository.get_team_members(db, current_user["id"])
            return {
                "members": [
                    {"id": m.id, "name": m.name, "email": m.email, "created_at": m.created_at}
                    for m in members
                ],
                "scope": "team",
            }
        # HR : vue globale
        members = user_repository.get_all_members(db)
        return {
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "email": m.email,
                    "role": m.role,
                    "manager_id": m.manager_id,
                    "created_at": m.created_at,
                }
                for m in members
            ],
            "scope": "all",
        }


# ============================================================================
# ADMINISTRATION DES COMPTES (réservé HR/ADMIN)
# ============================================================================
def _user_admin_dict(u) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "manager_id": u.manager_id,
        "entity": u.entity,
        "active": bool(getattr(u, "active", 1)),
        "created_at": u.created_at,
    }


def admin_list_users(current_user: dict) -> dict:
    """Liste tous les comptes (administration)."""
    require_super_admin(current_user)
    with db_session() as db:
        users = user_repository.list_all_ordered(db)
        return {"users": [_user_admin_dict(u) for u in users], "total": len(users)}


def admin_create_user(current_user: dict, request) -> dict:
    """Crée un compte (email unique, mot de passe haché)."""
    require_super_admin(current_user)
    email = (request.email or "").strip().lower()
    if not is_valid_bnp_email(email):
        raise HTTPException(
            status_code=400, detail="L'email doit être au format prenom.nom@bmci.local."
        )
    with db_session() as db:
        if user_repository.get_by_email(db, email):
            raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email.")
        user_id = f"user-{secrets.token_hex(4)}"
        user_repository.create(
            db,
            user_id=user_id,
            email=email,
            password_hash=security.hash_password(request.password),
            name=request.name.strip(),
            role=request.role,
            manager_id=(request.manager_id or None),
            entity=(request.entity or None),
        )
    return {"success": True, "id": user_id}


def admin_update_user(current_user: dict, user_id: str, request) -> dict:
    """Met à jour un compte (nom, rôle, manager, entité)."""
    require_super_admin(current_user)
    with db_session() as db:
        target = user_repository.get_by_id(db, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Compte introuvable.")
        values = {}
        if request.name is not None:
            values["name"] = request.name.strip()
        if request.manager_id is not None:
            values["manager_id"] = request.manager_id or None
        if request.entity is not None:
            values["entity"] = request.entity or None
        if request.role is not None and request.role != target.role:
            if (
                target.role == "HR"
                and target.active == 1
                and user_repository.count_active_by_role(db, "HR") <= 1
            ):
                raise HTTPException(
                    status_code=400, detail="Impossible : c'est le dernier compte RH actif."
                )
            values["role"] = request.role
        user_repository.update_fields(db, user_id, values)
    return {"success": True, "id": user_id}


def admin_set_user_active(current_user: dict, user_id: str, active: bool) -> dict:
    """Active ou désactive un compte (données conservées ; sessions purgées si désactivé)."""
    require_super_admin(current_user)
    if not active and user_id == current_user["id"]:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte."
        )
    with db_session() as db:
        target = user_repository.get_by_id(db, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Compte introuvable.")
        if (
            not active
            and target.role == "HR"
            and user_repository.count_active_by_role(db, "HR") <= 1
        ):
            raise HTTPException(
                status_code=400, detail="Impossible : c'est le dernier compte RH actif."
            )
        user_repository.set_active(db, user_id, active)
        if not active:
            session_repository.delete_by_user(db, user_id)
    return {"success": True, "id": user_id, "active": active}


def admin_reset_password(current_user: dict, user_id: str, new_password: str) -> dict:
    """Réinitialise le mot de passe d'un compte."""
    require_super_admin(current_user)
    with db_session() as db:
        target = user_repository.get_by_id(db, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Compte introuvable.")
        user_repository.update_password_hash(db, user_id, security.hash_password(new_password))
    return {"success": True, "id": user_id}


def admin_delete_user(current_user: dict, user_id: str) -> dict:
    """Supprime définitivement un compte (cascade objectifs/sessions)."""
    require_super_admin(current_user)
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=400, detail="Vous ne pouvez pas supprimer votre propre compte."
        )
    with db_session() as db:
        target = user_repository.get_by_id(db, user_id)
        if target is None:
            raise HTTPException(status_code=404, detail="Compte introuvable.")
        if (
            target.role == "HR"
            and target.active == 1
            and user_repository.count_active_by_role(db, "HR") <= 1
        ):
            raise HTTPException(
                status_code=400, detail="Impossible : c'est le dernier compte RH actif."
            )
        user_repository.delete_by_id(db, user_id)
    return {"success": True}
