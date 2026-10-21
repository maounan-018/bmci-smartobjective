#!/usr/bin/env python3
"""
services/permission_service.py — Vérification des droits d'accès (autorisation).

RÔLE
    Centralise les règles de permission par rôle. Tout service/contrôleur exposant
    des données sensibles doit appeler ces fonctions. Le frontend peut masquer des
    éléments, mais SEUL ce service autorise/refuse réellement l'accès.

    Les vérifications dépendant de la base (équipe d'un manager, périmètre de
    données) passent par le repository utilisateur (SQLAlchemy ORM).

RÔLES : COLLAB, MANAGER, HR, ADMIN (ADMIN réservé à l'évolution future).

EMPLACEMENT MVC
    Couche "services" : logique d'autorisation, séparée de l'authentification.
"""

from app.database.session import db_session
from app.repositories import user_repository
from fastapi import HTTPException, status


def require_role(current_user: dict, allowed_roles: list[str]) -> None:
    """Lève 403 si le rôle de l'utilisateur n'est pas autorisé."""
    if current_user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Accès refusé. Rôle requis : {', '.join(allowed_roles)}",
        )


def require_admin(current_user: dict) -> None:
    """
    Réserve l'accès aux fonctions d'administration « métier » (journal d'audit) :
    ADMIN et HR (la RH garde une visibilité sur la traçabilité).
    """
    if current_user.get("role") not in ("HR", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs."
        )


def require_super_admin(current_user: dict) -> None:
    """Réserve l'accès à l'ADMIN dédié UNIQUEMENT (gestion des comptes utilisateurs).
    La RH n'est PAS administrateur des comptes."""
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé à l'administrateur."
        )


def require_own_resource(current_user: dict, resource_user_id: str) -> None:
    """Un utilisateur n'accède qu'à ses propres ressources (ADMIN excepté)."""
    if current_user.get("role") == "ADMIN":
        return
    if current_user.get("id") != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez accéder qu'à vos propres données.",
        )


# ============= RBAC MÉTIER (périmètre de données par rôle) =============


def check_collab_access(current_user: dict, target_user_id: str) -> None:
    """Un collaborateur ne peut accéder qu'à SES propres données."""
    if current_user["role"] == "COLLAB" and current_user["id"] != target_user_id:
        raise HTTPException(
            status_code=403, detail="Accès refusé. Vous ne pouvez voir que vos propres données."
        )


def check_manager_access(current_user: dict, target_user_id: str) -> None:
    """Un manager ne peut accéder qu'aux collaborateurs rattachés à lui."""
    if current_user["role"] == "MANAGER":
        with db_session() as db:
            manager_id = user_repository.get_manager_id(db, target_user_id)
            if manager_id != current_user["id"]:
                raise HTTPException(
                    status_code=403,
                    detail="Accès refusé. Ce collaborateur n'est pas dans votre équipe.",
                )


def get_accessible_user_ids(current_user: dict) -> list[str]:
    """
    Retourne la liste des user_ids accessibles selon le rôle (RÈGLE STRICTE) :
      - COLLAB  : uniquement ses propres données
      - MANAGER : uniquement son équipe (manager_id = current_user.id)
      - HR      : tous les utilisateurs (analytics globaux uniquement)
    """
    if current_user["role"] == "COLLAB":
        return [current_user["id"]]

    if current_user["role"] == "MANAGER":
        with db_session() as db:
            return user_repository.get_team_ids(db, current_user["id"])

    if current_user["role"] == "HR":
        with db_session() as db:
            return user_repository.get_all_ids(db)

    return []


def get_manager_team_ids(manager_id: str) -> list[str]:
    """Retourne uniquement les IDs des collaborateurs d'un manager donné."""
    with db_session() as db:
        return user_repository.get_team_ids(db, manager_id)
