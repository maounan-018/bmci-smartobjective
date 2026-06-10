#!/usr/bin/env python3
"""
models/sso_code.py — Modèle ORM `SsoCode` (table `sso_codes`).

RÔLE
    Matérialise un code SSO à usage unique, émis après une assertion SAML
    vérifiée et échangé par le frontend contre un token de session. Le code
    permet de NE PAS faire transiter le token dans l'URL de redirection.

    Persisté en base (et non en mémoire) pour fonctionner derrière plusieurs
    workers/processus : un code émis par un worker doit être échangeable par
    n'importe quel autre.

SÉCURITÉ
    - On stocke le HASH du code (jamais le code en clair) : une fuite de la table
      n'expose aucun code réutilisable. Le code ne vit que dans l'URL de
      redirection, le temps de l'échange.
    - La table ne contient AUCUN token de session : elle mappe un code vers un
      `user_id`. La session (et donc le token) n'est créée qu'à l'échange.
    - Usage unique (ligne supprimée à la consommation) + TTL court (expires_at).

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SsoCode(Base):
    __tablename__ = "sso_codes"

    # Hash SHA-256 du code (jamais le code en clair). Clé primaire = anti-doublon.
    code_hash: Mapped[str] = mapped_column(String, primary_key=True)
    # Utilisateur déjà provisionné (JIT) auquel ce code donne droit à une session.
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    # Expiration ISO (cohérent avec la table sessions) : au-delà, code invalide.
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
