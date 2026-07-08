#!/usr/bin/env python3
"""
create_user.py — Provisionnement d'utilisateurs en base (avec rôle).

OUTIL D'ADMINISTRATION (ligne de commande). Remplace l'inscription publique
(supprimée pour raisons de sécurité) : c'est l'administrateur qui crée les
comptes, directement en base, avec le rôle voulu. Aucun self-service, aucune
escalade de rôle possible.

À lancer depuis le dossier backend/ :

  # Créer un compte (mot de passe choisi)
  python create_user.py --email rh@bmci.ma --name "RH BMCI" --role HR --password "MotDePasseFort1"

  # Créer un COLLAB rattaché à un manager existant
  python create_user.py --email collab@bmci.ma --name "Collab" --role COLLAB --manager manager@bmci.ma

  # Sans --password : un mot de passe fort est généré et affiché
  python create_user.py --email mgr@bmci.ma --role MANAGER

  # Lister les comptes existants
  python create_user.py --list

Rôles autorisés : COLLAB, MANAGER, HR.
"""

import argparse
import secrets
import sys

from app.core.emails import is_valid_bnp_email
from app.core.security import hash_password
from app.database.init_db import init_db
from app.database.session import db_session
from app.repositories import user_repository

ROLES = {"COLLAB", "MANAGER", "HR", "ADMIN"}
MIN_PASSWORD_LEN = 8


def _list_users() -> None:
    with db_session() as db:
        ids = user_repository.get_all_ids(db)
        if not ids:
            print("(aucun utilisateur en base)")
            return
        print(f"{'RÔLE':8}  {'EMAIL':32}  NOM")
        print("-" * 60)
        for uid in ids:
            u = user_repository.get_by_id(db, uid)
            print(f"{u.role:8}  {u.email:32}  {u.name or ''}")


def _create_user(args) -> None:
    role = (args.role or "").strip().upper()
    if role not in ROLES:
        sys.exit(f"[ERREUR] Rôle invalide : '{args.role}' (attendu : COLLAB | MANAGER | HR | ADMIN)")

    email = (args.email or "").strip().lower()
    if not is_valid_bnp_email(email):
        sys.exit(f"[ERREUR] Email invalide : '{args.email}' (format attendu : prenom.nom@bmci.local)")

    password = args.password or secrets.token_urlsafe(12)
    if len(password) < MIN_PASSWORD_LEN:
        sys.exit(f"[ERREUR] Mot de passe trop court (minimum {MIN_PASSWORD_LEN} caractères).")

    with db_session() as db:
        if user_repository.get_by_email(db, email):
            sys.exit(f"[ERREUR] L'email {email} existe déjà. Aucune modification effectuée.")

        manager_id = None
        if args.manager:
            mgr = user_repository.get_by_email(db, args.manager.strip().lower())
            if not mgr:
                sys.exit(f"[ERREUR] Manager introuvable : {args.manager}")
            if mgr.role != "MANAGER":
                sys.exit(f"[ERREUR] {args.manager} n'a pas le rôle MANAGER.")
            manager_id = mgr.id

        user_id = f"user-{secrets.token_hex(4)}"
        user_repository.create(
            db,
            user_id=user_id,
            email=email,
            password_hash=hash_password(password),
            name=args.name or email,
            role=role,
            manager_id=manager_id,
        )

    print(f"[OK] Utilisateur créé : {email}  (rôle={role}, id={user_id})")
    if not args.password:
        print(f"     Mot de passe généré : {password}")
        print("     (à transmettre de façon sécurisée ; à changer si possible)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provisionnement d'utilisateurs en base (avec rôle).",
    )
    parser.add_argument("--email", help="Email du compte")
    parser.add_argument("--name", default="", help="Nom complet affiché")
    parser.add_argument("--role", help="COLLAB | MANAGER | HR")
    parser.add_argument("--password", help="Mot de passe (sinon généré aléatoirement)")
    parser.add_argument("--manager", help="Email du manager (pour un COLLAB)")
    parser.add_argument("--list", action="store_true", help="Lister les comptes existants")
    args = parser.parse_args()

    init_db()  # garantit l'existence des tables

    if args.list:
        _list_users()
        return

    if not args.email or not args.role:
        parser.error("--email et --role sont obligatoires (ou utilisez --list).")

    _create_user(args)


if __name__ == "__main__":
    main()
