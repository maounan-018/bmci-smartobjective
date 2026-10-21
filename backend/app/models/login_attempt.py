#!/usr/bin/env python3
"""
models/login_attempt.py — Modèle ORM `LoginAttempt` (table `login_attempts`).

RÔLE
    Matérialise une tentative de connexion ÉCHOUÉE pour l'anti brute-force.
    Chaque échec = une ligne (identifiant + horodatage ISO). Le comptage des
    tentatives récentes dans la fenêtre glissante remplace l'ancien dictionnaire
    en mémoire : l'état est désormais PARTAGÉ entre tous les workers et SURVIT
    au redémarrage (indispensable dès qu'on sert avec plusieurs processus).

    `identifier` vaut soit l'email saisi, soit "ip:<adresse>" (blocage par email
    ET par IP, cf. auth_service.login / services/throttle_service).

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from app.database.base import Base
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Email saisi OU "ip:<adresse>" — clé de regroupement du rate limiting.
    identifier: Mapped[str] = mapped_column(String, nullable=False)
    # Horodatage ISO 8601 (str), cohérent avec le reste du projet (sessions, etc.).
    attempted_at: Mapped[str] = mapped_column(String, nullable=False)

    # Index composite : le comptage filtre sur (identifier, attempted_at > fenêtre).
    __table_args__ = (Index("ix_login_attempts_identifier_time", "identifier", "attempted_at"),)
