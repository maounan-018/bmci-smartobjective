#!/usr/bin/env python3
"""
models/ai_call.py — Modèle ORM `AiCall` (table `ai_calls`).

RÔLE
    Trace chaque appel d'analyse IA (1 appel = 1 ligne : utilisateur + horodatage)
    pour le rate limiting anti-saturation d'Ollama. Le modèle local ne traite
    qu'une requête à la fois : sans garde-fou, un utilisateur pourrait empiler des
    dizaines d'analyses (30 s–2 min chacune) et bloquer le service pour tous.

    Le comptage des appels récents dans une fenêtre glissante (cf.
    services/ai_rate_limit_service) borne le débit PAR UTILISATEUR. L'état est en
    base : il fonctionne en multi-worker et survit au redémarrage.

EMPLACEMENT MVC
    Couche "models" : structure des données persistées.
"""

from app.database.base import Base
from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class AiCall(Base):
    __tablename__ = "ai_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    # Horodatage ISO 8601 (str), cohérent avec le reste du projet.
    called_at: Mapped[str] = mapped_column(String, nullable=False)

    # Index composite : le comptage filtre sur (user_id, called_at > fenêtre).
    __table_args__ = (Index("ix_ai_calls_user_time", "user_id", "called_at"),)
