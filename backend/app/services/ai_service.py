#!/usr/bin/env python3
"""
services/ai_service.py — Service d'analyse IA (Ollama).

RÔLE
    Centralise TOUTE la logique d'appel au modèle local Ollama et la validation
    des résultats SMART / alignement :
      - heuristiques (has_measure, has_time) et cohérence (enforce_consistency)
      - extraction tolérante du JSON renvoyé par le modèle
      - appel HTTP au modèle (call_ollama)
      - analyses réutilisables (analyze_smart_internal, analyze_alignment_internal,
        analyze_objectives_batch)

SÉCURITÉ
    Aucun secret n'est logué. L'URL et le nom du modèle proviennent de la config
    (.env), jamais codés en dur. Le backend reste la source de vérité.

EMPLACEMENT MVC
    Couche "services" : logique métier IA, sans route HTTP.
"""

import re
import json
import logging

import requests
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============= HEURISTIQUES =============

def has_measure(text: str) -> bool:
    """Détecte la présence d'un indicateur mesurable (chiffre, KPI, niveau...)."""
    if re.search(r"\d", text):
        return True
    if re.search(r"\b(A1|A2|B1|B2|C1|C2)\b", text, flags=re.IGNORECASE):
        return True
    keywords = ["kpi", "score", "nps", "taux", "%", "pourcent", "clients", "ventes",
                "vues", "minutes", "heures", "tests", "mock", "toeic", "ielts", "toefl",
                "chiffre", "nombre", "quantité", "objectif", "cible", "ratio", "indice"]
    return any(k in text.lower() for k in keywords)


def has_time(text: str) -> bool:
    """Détecte la présence d'une échéance temporelle (date, durée, période...)."""
    t = text.lower()
    if re.search(r"\b(\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?)\b", t):
        return True
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", t):
        return True
    temporal_keywords = [
        "d'ici", "avant", "au plus tard", "délai", "deadline", "by", "before", "within",
        "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre", "trimestre", "semestre",
        "annuel", "mensuel", "hebdomadaire", "fin d'année", "2024", "2025", "2026",
        "q1", "q2", "q3", "q4", "t1", "t2", "t3", "t4"
    ]
    if any(k in t for k in temporal_keywords):
        return True
    if re.search(r"\b(en|in|dans)\s+\d+\s+(jour|jours|semaine|semaines|mois|an|ans|day|days|week|weeks|month|months|year|years)\b", t):
        return True
    return False


def enforce_consistency(res: dict, objective: str) -> dict:
    """Corrige les incohérences du modèle (M/T affirmés sans preuve) et recalcule overall."""
    if "issues" not in res or not isinstance(res["issues"], list):
        res["issues"] = []

    present_letters = {it.get("letter") for it in res.get("issues", []) if isinstance(it, dict)}
    for L in ["S", "M", "A", "R", "T"]:
        if res.get(L) is False and L not in present_letters:
            res["issues"].append({
                "letter": L,
                "problem": f"Critère {L} non satisfait.",
                "fix": f"Préciser davantage pour respecter le critère {L}."
            })

    full_text = f"{objective} {res.get('rewrite_fr', '')} {res.get('rewrite_en', '')}"

    if res.get("M") and not has_measure(full_text):
        res["M"] = False
        if "M" not in present_letters:
            res["issues"].append({
                "letter": "M",
                "problem": "Mesurable=true mais aucun indicateur chiffré détecté.",
                "fix": "Ajouter un KPI, pourcentage, nombre cible ou indicateur vérifiable."
            })

    if res.get("T") and not has_time(full_text):
        res["T"] = False
        if "T" not in present_letters:
            res["issues"].append({
                "letter": "T",
                "problem": "Time-bound=true mais aucune échéance détectée.",
                "fix": "Ajouter une date limite ou une durée (ex: d'ici le 31 décembre 2025)."
            })

    res["overall"] = bool(res.get("S") and res.get("M") and res.get("A") and res.get("R") and res.get("T"))
    return res


def extract_json_from_text(text: str) -> dict:
    """Extrait un objet JSON d'une réponse potentiellement bruitée (markdown, texte)."""
    text = text.strip()

    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    first_brace = text.find('{')
    last_brace = text.rfind('}')

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = text[first_brace:last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    cleaned = text.replace('\n', ' ').replace('\r', '')
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')

    if first_brace != -1 and last_brace != -1:
        json_str = cleaned[first_brace:last_brace + 1]
        return json.loads(json_str)

    raise json.JSONDecodeError("No valid JSON found", text, 0)


def _post_to_ollama(prompt: str, system: str) -> str:
    """Un seul appel HTTP à Ollama ; renvoie le texte brut du champ 'response'.

    Les erreurs d'INFRASTRUCTURE (Ollama éteint, timeout) lèvent une HTTPException
    et ne sont PAS réessayées par call_ollama (un nouvel essai n'y changerait rien)."""
    full_prompt = f"/no_think\n{prompt}"
    try:
        response = requests.post(
            settings.OLLAMA_URL,
            json={
                "model": settings.OLLAMA_MODEL,
                "system": system,
                "prompt": full_prompt,
                "stream": False,
                "format": "json",
            },
            timeout=180,
        )
        response.raise_for_status()
        return response.json().get("response", "{}")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Ollama n'est pas démarré. Lancez 'ollama serve' puis réessayez.")
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Le modèle met trop de temps à répondre.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erreur Ollama: %s", e)
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'analyse IA.")


def call_ollama(prompt: str, system: str, is_valid=None) -> dict:
    """Appelle Ollama et renvoie le JSON extrait, AVEC RÉESSAI.

    Le modèle local renvoie de temps à autre un JSON vide ({}) ou du texte non
    parsable. Sans réessai, l'appelant retombe alors sur ses valeurs par défaut —
    d'où l'analyse dégradée « tout faux, sans reformulation » vue côté utilisateur.
    On réessaie donc tant que la réponse est vide, non parsable, ou refusée par
    `is_valid`, dans la limite de settings.AI_MAX_ATTEMPTS essais. Les erreurs
    d'infrastructure (503/504) remontent immédiatement (réessai inutile).

    `is_valid(dict) -> bool` laisse chaque appelant définir une réponse exploitable
    (présence des critères SMART, d'un score d'alignement, …).
    """
    attempts = max(1, settings.AI_MAX_ATTEMPTS)
    last_result: dict = {}
    parsed_ever = False

    for attempt in range(1, attempts + 1):
        text = _post_to_ollama(prompt, system)  # 503/504 propagés immédiatement
        # Trace VERBEUSE en debug uniquement : contient le contenu analysé (données
        # RH). En prod (LOG_LEVEL=INFO) elle est masquée -> aucune fuite dans les logs.
        logger.debug("Ollama réponse (essai %d/%d): %s...", attempt, attempts, text[:300])
        try:
            result = extract_json_from_text(text)
        except json.JSONDecodeError:
            continue  # réponse non parsable -> nouvel essai
        parsed_ever = True
        if result and (is_valid is None or is_valid(result)):
            return result
        last_result = result or last_result
        # réponse vide ou incomplète -> nouvel essai

    if not parsed_ever:
        # Aucune réponse parsable, même après réessais (texte systématiquement bruité).
        raise HTTPException(status_code=500, detail="Réponse IA invalide (JSON malformé).")
    # Réponses parsables mais vides/incomplètes : on rend le dernier dict obtenu ;
    # l'appelant le complète avec ses valeurs par défaut (repli historique).
    return last_result


# ============= ANALYSES RÉUTILISABLES =============

def _smart_response_ok(result: dict) -> bool:
    """Réponse SMART exploitable : le modèle a réellement évalué les critères
    (au moins une lettre S/M/A/R/T présente), et pas seulement renvoyé un {} vide."""
    return any(k in result for k in ("S", "M", "A", "R", "T"))


def _alignment_response_ok(result: dict) -> bool:
    """Réponse d'alignement exploitable : présence d'un score ou de correspondances."""
    return "alignment_score" in result or "top_matches" in result


def analyze_smart_internal(title: str, description: str = None) -> dict:
    """Analyse SMART d'un objectif — réutilisable par tous les domaines."""
    system_prompt = """Tu es un expert RH de la BMCI (Banque Marocaine pour le Commerce et l'Industrie).
Tu analyses les objectifs selon la méthode SMART (Spécifique, Mesurable, Atteignable, Réaliste, Temporel).

RÈGLES STRICTES:
- S (Spécifique): L'objectif doit être clair, précis, sans ambiguïté.
- M (Mesurable): Il DOIT y avoir un indicateur chiffré (%, nombre, score, KPI). Sans chiffre = M = false.
- A (Atteignable): L'objectif doit être ambitieux mais réalisable.
- R (Réaliste): L'objectif doit être pertinent par rapport au poste.
- T (Temporel): Il DOIT y avoir une date limite. Sans date = T = false.

overall = true UNIQUEMENT si S ET M ET A ET R ET T sont tous true.

Retourne UNIQUEMENT un JSON valide:
{
  "S": boolean,
  "M": boolean,
  "A": boolean,
  "R": boolean,
  "T": boolean,
  "overall": boolean,
  "confidence": number (0.0 à 1.0),
  "issues": [{"letter": "S|M|A|R|T", "problem": "description", "fix": "suggestion"}],
  "rewrite_fr": "Version améliorée en français",
  "rewrite_en": "Improved English version"
}"""

    prompt = f"""Analyse cet objectif BMCI:

Titre: {title}
Description: {description or 'Non fournie'}

Évalue chaque critère SMART avec rigueur."""

    result = call_ollama(prompt, system_prompt, is_valid=_smart_response_ok)

    defaults = {
        "S": False, "M": False, "A": False, "R": False, "T": False,
        "overall": False, "confidence": 0.5, "issues": [],
        "rewrite_fr": title, "rewrite_en": title
    }
    for key, default_val in defaults.items():
        if key not in result:
            result[key] = default_val

    result = enforce_consistency(result, f"{title} {description}")

    return result


def analyze_alignment_internal(objective_title: str, company_objectives: list) -> dict:
    """Analyse d'alignement stratégique d'un objectif — réutilisable."""
    catalogue_str = "\n".join([
        f"- [{obj.get('id', 'N/A')}] {obj.get('title', '')} : {obj.get('description', '')}"
        for obj in company_objectives
    ])

    system_prompt = """Tu es un expert en stratégie d'entreprise à la BMCI.
Tu évalues l'alignement des objectifs individuels avec les priorités stratégiques.

Retourne UNIQUEMENT un JSON valide:
{
  "alignment_score": number (0 à 100),
  "top_matches": [
    {"objective_id": "ID", "score": number (0-100), "reason": "Explication"}
  ],
  "gaps": ["Liste des lacunes"]
}

Maximum 3 correspondances dans top_matches."""

    prompt = f"""Évalue l'alignement stratégique:

OBJECTIF: "{objective_title}"

PRIORITÉS STRATÉGIQUES BMCI:
{catalogue_str}

Calcule un score d'alignement global."""

    try:
        result = call_ollama(prompt, system_prompt, is_valid=_alignment_response_ok)

        if "alignment_score" not in result:
            result["alignment_score"] = 50
        if "top_matches" not in result:
            result["top_matches"] = []
        if "gaps" not in result:
            result["gaps"] = []

        result["top_matches"] = result["top_matches"][:3]

        return result
    except HTTPException:
        return {
            "alignment_score": 50,
            "top_matches": [],
            "gaps": ["Analyse d'alignement non disponible"]
        }
