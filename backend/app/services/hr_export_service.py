#!/usr/bin/env python3
"""
services/hr_export_service.py — Exports Excel/PDF du domaine RH.

RÔLE
    Construit les rapports RH (Excel multi-feuilles, PDF synthétique) à partir des
    agrégats du repository, puis délègue la génération du document à export_service.

EMPLACEMENT MVC
    Couche "services" : logique métier RH (exports).
"""

from app.database.session import db_session
from app.repositories import analysis_repository
from app.services import export_service, ai_service
from app.services.hr_common import require_hr

_CRITERIA = [
    ("S - Spécifique", "s_score"),
    ("M - Mesurable", "m_score"),
    ("A - Atteignable", "a_score"),
    ("R - Réaliste", "r_score"),
    ("T - Temporel", "t_score"),
]


def export_excel(current_user: dict, entity=None, manager=None, period=None):
    """Construit le rapport Excel multi-feuilles RH."""
    require_hr(current_user)
    with db_session() as db:
        detailed = analysis_repository.hr_export_detailed(db, entity, manager, period)
        entity_stats = analysis_repository.hr_export_entity_stats(db, entity, manager, period)
        manager_stats = analysis_repository.hr_export_manager_stats(db, entity, manager, period)
        total_obj = analysis_repository.hr_count_objectives(db, entity, manager, period) or 1
        failures = [
            (label, analysis_repository.hr_criteria_failures(db, col, entity, manager, period))
            for label, col in _CRITERIA
        ]
    return export_service.generate_hr_excel(detailed, entity_stats, manager_stats, total_obj, failures)


def export_pdf(current_user: dict, entity=None, manager=None, period=None):
    """Construit le rapport COMEX (Direction) : photo de la campagne, KPI + paragraphes
    IA observationnels. AUCUNE comparaison (personnes, entités, périodes), AUCUN nom.

    Le PDF s'appuie sur les agrégats déjà calculés (get_analytics). Les paragraphes
    sont générés par l'IA à partir de CHIFFRES AGRÉGÉS uniquement (donc impossible de
    nommer/juger une personne) ; si le modèle est indisponible, un repli factuel est
    utilisé et le PDF se génère quand même.
    """
    require_hr(current_user)
    # Import tardif : évite tout cycle d'import au chargement du module.
    from app.services import hr_analysis_service
    data = hr_analysis_service.get_analytics(current_user, entity, manager, period)

    avg = data.get("avg_scores", {}) or {}
    sr = data.get("smart_rate", {}) or {}
    vol = data.get("volumetry", {}) or {}
    lc = data.get("low_confidence", {}) or {}
    cov = data.get("axis_coverage", {}) or {}
    thr = data.get("thresholds", {}) or {}
    axes = cov.get("axes") or []

    def r(x):
        return round(x or 0)

    to_adjust = max(0, (sr.get("total", 0) or 0) - (sr.get("ok", 0) or 0))
    orphans = [a.get("axis_title") for a in axes if a.get("orphan")]
    over = [a.get("axis_title") for a in axes if a.get("over_concentrated")]

    # Faits AGRÉGÉS et ANONYMES fournis au modèle (aucun nom, aucune comparaison).
    facts = {
        "analyzed": f"{vol.get('analyzed', 0)} objectifs analyses sur {vol.get('total', 0)} importes.",
        "smart_rate": f"taux d'objectifs SMART {r(sr.get('rate'))}% (cible {thr.get('smart', 80)}%), "
                      f"{sr.get('ok', 0)} sur {sr.get('total', 0)} conformes.",
        "avg_smart": f"score SMART moyen {r(avg.get('avg_smart'))}%.",
        "avg_alignment": f"alignement strategique moyen {r(avg.get('avg_alignment'))}%.",
        "to_adjust": f"{to_adjust} objectifs sous le seuil de conformite SMART.",
        "low_confidence": f"{lc.get('count', 0)} analyses sous le seuil de confiance IA "
                          f"{thr.get('ai_confidence_min', 0.6)}.",
        "quality": "taux de conformite par critere SMART : S {}%, M {}%, A {}%, R {}%, T {}%.".format(
            r((avg.get('avg_s') or 0) * 100), r((avg.get('avg_m') or 0) * 100),
            r((avg.get('avg_a') or 0) * 100), r((avg.get('avg_r') or 0) * 100),
            r((avg.get('avg_t') or 0) * 100)),
        "coverage": "couverture par axe : "
                    + "; ".join(f"{a.get('axis_title')} {a.get('share_pct')}%" for a in axes)
                    + f". Axes orphelins : {', '.join(orphans) if orphans else 'aucun'}. "
                    + f"Axes sur-concentres : {', '.join(over) if over else 'aucun'} "
                    + f"(seuil {thr.get('axis_over_concentration', 40)}%).",
        "attention": f"{to_adjust} objectifs a ajuster, {lc.get('count', 0)} analyses a faible confiance IA, "
                     f"{len(orphans)} axe(s) orphelin(s), {len(over)} axe(s) sur-concentre(s).",
    }

    # UN SEUL appel IA (constats par indicateur + synthèse) ; repli factuel côté rendu.
    report = ai_service.comex_report(facts)
    paragraphs = report.get("paragraphs", {})
    synthesis = report.get("synthesis", "")

    period_label = period or "Campagne en cours"
    return export_service.generate_hr_comex_pdf(data, paragraphs, synthesis, period_label)
