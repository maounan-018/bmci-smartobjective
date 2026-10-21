#!/usr/bin/env python3
"""
repositories/user_repository.py — Accès aux données `users` (+ jointure sessions).

RÔLE
    Encapsule toutes les requêtes ORM relatives aux utilisateurs : lecture par
    id/email, validation de session, création, migration de hash, périmètre
    d'équipe. Aucune requête utilisateur ne doit exister hors de ce module.

EMPLACEMENT MVC
    Couche "repositories" : accès aux données.
"""

from typing import Optional

from app.core.security import hash_token
from app.models.session import Session as SessionModel
from app.models.user import User
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session


def get_by_id(db: Session, user_id: str) -> Optional[User]:
    """Retourne l'utilisateur par identifiant, ou None."""
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> Optional[User]:
    """Retourne l'utilisateur par email (insensible aux espaces), ou None."""
    return db.scalars(select(User).where(User.email == email)).first()


def get_by_valid_session(db: Session, token: str, now_iso: str) -> Optional[User]:
    """Retourne l'utilisateur d'une session encore valide (hash du token + non expirée)."""
    stmt = (
        select(User)
        .join(SessionModel, User.id == SessionModel.user_id)
        .where(SessionModel.token == hash_token(token), SessionModel.expires_at > now_iso)
    )
    return db.scalars(stmt).first()


def create(
    db: Session,
    *,
    user_id: str,
    email: str,
    password_hash: str,
    name: str,
    role: str,
    manager_id: Optional[str] = None,
    entity: Optional[str] = None,
) -> User:
    """Crée un utilisateur et le rattache à la session (flush pour détecter les conflits)."""
    user = User(
        id=user_id,
        email=email,
        password_hash=password_hash,
        name=name,
        role=role,
        manager_id=manager_id,
        entity=entity,
    )
    db.add(user)
    db.flush()  # déclenche une éventuelle IntegrityError (email déjà utilisé)
    return user


def update_password_hash(db: Session, user_id: str, new_hash: str) -> None:
    """Met à jour le hash du mot de passe (migration transparente PBKDF2)."""
    db.execute(update(User).where(User.id == user_id).values(password_hash=new_hash))


def is_manager(db: Session, user_id: str) -> bool:
    """True si l'utilisateur existe et a le rôle MANAGER."""
    stmt = select(User.id).where(User.id == user_id, User.role == "MANAGER")
    return db.scalars(stmt).first() is not None


def get_manager_id(db: Session, user_id: str) -> Optional[str]:
    """Retourne le manager_id d'un utilisateur (None si introuvable)."""
    return db.scalars(select(User.manager_id).where(User.id == user_id)).first()


def get_team_ids(db: Session, manager_id: str) -> list[str]:
    """IDs des collaborateurs rattachés à un manager."""
    return list(db.scalars(select(User.id).where(User.manager_id == manager_id)).all())


def get_all_ids(db: Session) -> list[str]:
    """IDs de tous les utilisateurs (périmètre HR)."""
    return list(db.scalars(select(User.id)).all())


def get_team_members(db: Session, manager_id: str) -> list[User]:
    """Membres de l'équipe d'un manager."""
    return list(db.scalars(select(User).where(User.manager_id == manager_id)).all())


def get_all_members(db: Session) -> list[User]:
    """Tous les utilisateurs (vue HR globale)."""
    return list(db.scalars(select(User)).all())


def list_all_ordered(db: Session) -> list[User]:
    """Tous les utilisateurs, triés par rôle puis email (administration des comptes)."""
    return list(db.scalars(select(User).order_by(User.role, User.email)).all())


def count_active_by_role(db: Session, role: str) -> int:
    """Nombre de comptes ACTIFS pour un rôle (garde-fou « dernier administrateur »)."""
    return (
        db.scalar(select(func.count()).select_from(User).where(User.role == role, User.active == 1))
        or 0
    )


def set_active(db: Session, user_id: str, active: bool) -> None:
    """Active (1) ou désactive (0) un compte."""
    db.execute(update(User).where(User.id == user_id).values(active=1 if active else 0))


def update_fields(db: Session, user_id: str, values: dict) -> None:
    """Met à jour les champs fournis d'un utilisateur (nom, rôle, manager, entité)."""
    if values:
        db.execute(update(User).where(User.id == user_id).values(**values))


def delete_by_id(db: Session, user_id: str) -> bool:
    """Supprime un utilisateur (cascade objectifs/sessions). True si supprimé."""
    obj = db.get(User, user_id)
    if obj is None:
        return False
    db.delete(obj)
    return True
