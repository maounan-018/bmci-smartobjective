#!/usr/bin/env python3
"""
tests/test_ai_quickwins.py — Garde-fous IA issus de l'audit (confiance/conformité).

Verrouille, SANS appel réseau (Ollama monkeypatché ou fonctions pures) :
  - heuristiques M/T resserrées (plus de faux positifs),
  - M/T jugés sur l'objectif source, pas sur la reformulation du modèle,
  - issues A/R explicatives (contexte manquant + effet sur la note),
  - bornage de la confiance et du score d'alignement,
  - filtrage des identifiants d'alignement inventés,
  - reformulation non ancrée (hallucination) vidée sur objectif inutilisable.
"""
from app.services import ai_service as S


# ---------- Heuristiques resserrées ----------

def test_has_measure_rejette_noms_dactivite():
    assert S.has_measure("ameliorer la relation clients") is False
    assert S.has_measure("plan d'ici 2026") is False          # une annee seule n'est pas une mesure
    assert S.has_measure("reduire de 20%") is True
    assert S.has_measure("atteindre 55 de NPS") is True
    assert S.has_measure("niveau B2 en anglais") is True       # referentiel CEFR


def test_has_time_rejette_les_cadences():
    assert S.has_time("revue mensuelle") is False
    assert S.has_time("objectif annuel") is False
    assert S.has_time("d'ici le 31/12/2026") is True
    assert S.has_time("au T3 2026") is True


# ---------- M/T jugés sur la SOURCE, pas la reformulation ----------

def test_enforce_ne_valide_pas_M_T_via_le_rewrite():
    res = {"S": True, "M": True, "A": True, "R": True, "T": True,
           "rewrite_fr": "Augmenter X de 20% d'ici le 31/12/2026", "issues": []}
    out = S.enforce_consistency(res, "Ameliorer la satisfaction")  # source: ni chiffre ni date
    assert out["M"] is False
    assert out["T"] is False
    assert out["overall"] is False


# ---------- Issues A/R explicatives ----------

def test_issues_A_R_expliquent_le_contexte_manquant():
    out = S.enforce_consistency(
        {"S": True, "M": True, "A": False, "R": False, "T": True, "issues": []}, "obj")
    by = {i["letter"]: i for i in out["issues"]}
    assert "A" in by and ("moyen" in by["A"]["problem"].lower() or "point de départ" in by["A"]["problem"].lower())
    assert "R" in by and ("poste" in by["R"]["problem"].lower() or "stratég" in by["R"]["problem"].lower())


# ---------- Bornage confiance ----------

def test_confidence_bornee(monkeypatch):
    payload = ('{"S":true,"M":true,"A":true,"R":true,"T":true,"overall":true,'
               '"confidence":5,"issues":[],"rewrite_fr":"Augmenter ventes 10% en 2026",'
               '"rewrite_en":"Increase sales 10% in 2026"}')
    monkeypatch.setattr(S, "_post_to_ollama", lambda p, s: payload)
    res = S.analyze_smart_internal("Augmenter ventes de 10% en 2026", "")
    assert res["confidence"] == 1.0


# ---------- Reformulation non ancrée (hallucination) ----------

def test_ground_rewrite_vide_un_rewrite_non_ancre_si_objectif_inutilisable():
    res = {"overall": False, "confidence": 0.0,
           "rewrite_fr": "Reduire les incidents de securite bancaire de 30%", "issues": []}
    out = S.ground_rewrite(res, "azerty lorem ipsum dolor")  # aucun mot commun
    assert out["rewrite_fr"] == ""
    assert out["rewrite_en"] == ""


def test_ground_rewrite_conserve_un_rewrite_ancre():
    res = {"overall": False, "confidence": 0.2,
           "rewrite_fr": "Ameliorer la satisfaction via un score cible", "issues": []}
    out = S.ground_rewrite(res, "Ameliorer la satisfaction des collaborateurs")
    assert out["rewrite_fr"] != ""  # partage « ameliorer », « satisfaction »


def test_ground_rewrite_ne_touche_pas_un_objectif_confiant():
    res = {"overall": True, "confidence": 0.95, "rewrite_fr": "Texte totalement different", "issues": []}
    out = S.ground_rewrite(res, "azerty lorem ipsum")
    assert out["rewrite_fr"] == "Texte totalement different"


# ---------- Alignement : bornage + ids inventés écartés ----------

def test_alignment_borne_score_et_ecarte_ids_inventes(monkeypatch):
    payload = ('{"alignment_score":150,'
               '"top_matches":[{"objective_id":"AX1","score":90,"reason":"ok"},'
               '{"objective_id":"ZZ9","score":80,"reason":"invente"}],"gaps":[]}')
    monkeypatch.setattr(S, "_post_to_ollama", lambda p, s: payload)
    res = S.analyze_alignment_internal("obj", [{"id": "AX1", "title": "t", "description": "d"}])
    assert res["alignment_score"] == 100                       # borné à 100
    ids = [m["objective_id"] for m in res["top_matches"]]
    assert ids == ["AX1"]                                       # ZZ9 (inventé) écarté
