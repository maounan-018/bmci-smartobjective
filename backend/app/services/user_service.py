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

from fastapi import HTTPException

from app.database.session import db_session
from app.repositories import user_repository


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
                    "id": m.id, "name": m.name, "email": m.email,
                    "role": m.role, "manager_id": m.manager_id, "created_at": m.created_at,
                }
                for m in members
            ],
            "scope": "all",
        }
