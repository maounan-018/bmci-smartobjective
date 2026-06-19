#!/usr/bin/env python3
"""
schemas/chat_schema.py — Schémas Pydantic pour le Coach IA (stateless).

L'historique complet est renvoyé à chaque tour (aucune session serveur) : le
backend reste sans état, ce qui simplifie l'injection de contexte RAG.

EMPLACEMENT MVC
    Couche "schemas" : contrats d'entrée/sortie du chatbot.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Un message dans l'historique de conversation."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """Payload entrant pour POST /api/chat-coach."""
    messages: List[ChatMessage] = Field(..., min_length=1, max_length=50)

    @field_validator("messages")
    @classmethod
    def must_end_with_user(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        if v and v[-1].role != "user":
            raise ValueError("Le dernier message doit venir de l'utilisateur.")
        return v


class ChatResponse(BaseModel):
    """Réponse du Coach IA."""
    reply: str
    ready: bool = False
    final_objective: Optional[str] = None
    current_step: Optional[str] = None
    # Revalidation SMART de l'objectif final par le pipeline d'analyse (S/M/A/R/T,
    # overall, issues...) : présent uniquement quand un objectif final est produit.
    smart_validation: Optional[dict] = None
