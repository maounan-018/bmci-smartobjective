#!/usr/bin/env python3
"""
database/seed.py — Comptes de démonstration (seeding idempotent).

RÔLE
    Crée, au démarrage, les comptes de démonstration (Manager, RH, Collaborateur)
    s'ils n'existent pas encore. Garantit qu'une COPIE ou un CLONE du projet est
    immédiatement utilisable : l'écran de connexion fonctionne sans étape manuelle.

IDEMPOTENT
    Chaque compte n'est créé que si son email est absent. Relancer l'application
    ne duplique rien et n'écrase aucune donnée existante.

SÉCURITÉ
    Les mots de passe proviennent du .env (SEED_*_PASSWORD) et sont hachés en
    PBKDF2 comme tout autre compte. Désactivable via SEED_DEMO_ACCOUNTS=false
    (à faire en production). Mots de passe de démo À CHANGER hors développement.

EMPLACEMENT MVC
    Couche "database" : amorçage des données initiales.
"""

from app.core.config import settings
from app.core.emails import to_bnp_email
from app.core.security import hash_password
from app.database.session import db_session
from app.repositories import user_repository


def _ensure_user(db, *, user_id, email, name, role, password, manager_id=None) -> None:
    """Crée le compte s'il n'existe pas déjà (par email). Sans mot de passe → ignoré."""
    if not password:
        return
    if user_repository.get_by_email(db, email):
        return
    user_repository.create(
        db,
        user_id=user_id,
        email=email,
        password_hash=hash_password(password),
        name=name,
        role=role,
        manager_id=manager_id,
    )


def seed_demo_accounts() -> None:
    """Crée le compte ADMIN (dédié) puis les comptes de démo (Manager/RH/Collab).

    Emails au format entreprise `prenom.nom@bmci.local`. Ne sème RIEN si la
    connexion locale est désactivée (SSO réel) : inutile de créer des comptes à
    mots de passe faibles qui ne pourraient servir que de porte dérobée.
    """
    if not settings.local_auth_enabled:
        return

    with db_session() as db:
        # 0) Compte ADMIN dédié — indépendant des comptes de démonstration.
        _ensure_user(
            db,
            user_id="user-admin",
            email=settings.SEED_ADMIN_EMAIL,
            name="Admin System",
            role="ADMIN",
            password=settings.SEED_ADMIN_PASSWORD,
        )

        if not settings.SEED_DEMO_ACCOUNTS:
            return

        # 1) Manager et RH (emails dérivés du nom).
        _ensure_user(
            db,
            user_id="user-seed-manager",
            email=to_bnp_email("Manager Démo"),
            name="Manager Démo",
            role="MANAGER",
            password=settings.SEED_MANAGER_PASSWORD,
        )
        _ensure_user(
            db,
            user_id="user-seed-hr",
            email=to_bnp_email("RH Démo"),
            name="RH Démo",
            role="HR",
            password=settings.SEED_HR_PASSWORD,
        )

        # 2) Collaborateur rattaché au manager de démo (résolution par id, robuste).
        manager = user_repository.get_by_id(db, "user-seed-manager")
        _ensure_user(
            db,
            user_id="user-seed-collab",
            email=to_bnp_email("Collaborateur Démo"),
            name="Collaborateur Démo",
            role="COLLAB",
            password=settings.SEED_COLLAB_PASSWORD,
            manager_id=manager.id if manager else None,
        )
