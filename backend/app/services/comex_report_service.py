#!/usr/bin/env python3
"""
services/comex_report_service.py — Rapport Direction / COMEX (PDF front-loaded).

RÔLE
    Génère le rapport de pilotage destiné à la Direction / COMEX sous forme d'un
    PDF portrait soigné : chaque section est un PANNEAU-DASHBOARD composé en
    matplotlib (cartes KPI, treemap, donuts, heatmap, barres de taux...), assemblé
    en PDF via reportlab. Le rendu reprend le style des écrans RH.

    Toutes les valeurs proviennent des agrégats déjà calculés par
    hr_analysis_service.get_analytics (taux SMART, par critère, couverture par
    axe, distributions, comparatifs entités/managers). La synthèse est ancrée
    dans les chiffres réels — jamais de tendance inventée (anti-hallucination).

    Visuels volontairement EXCLUS (choix produit) : matrice SMART×Alignement,
    courbe d'évolution, histogramme de dispersion, radar, priorité×couverture,
    et comparaison multi-campagnes (pas d'historique de campagnes dans l'app).
    Aucun delta « vs N-1 » n'est affiché tant qu'il n'existe qu'une campagne.

EMPLACEMENT MVC
    Couche "services" : génération de document, sans route HTTP.
"""

import io
import json
import logging
import textwrap
from datetime import datetime

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

# Palette (style BI moderne : émeraude BMCI + neutres froids) — chaînes pures.
BG, CARD, CARD_BORDER = "#f3f5f9", "#ffffff", "#e7ecf3"
INK, MUTED, FAINT = "#1f2733", "#6b7787", "#9aa6b6"
GREEN, GREEN_D, SKY = "#10b981", "#047857", "#3b82f6"
AMBER, RED, VIOLET, TEAL, SLATE = "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#94a3b8"
GRID = "#eef2f7"
RED_BMCI = "#c8102e"
PALETTE = [GREEN, SKY, AMBER, VIOLET, TEAL, "#f43f5e", "#6366f1", SLATE]

try:
    import matplotlib
    matplotlib.use("Agg")
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle
    import matplotlib.patches as mpatches
    from matplotlib.colors import LinearSegmentedColormap
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors as rl
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                    Spacer, Image, Table, TableStyle, PageBreak)
    HEAT_CMAP = LinearSegmentedColormap.from_list(
        "bmci_heat", ["#e4715f", "#efa24f", "#f6d06a", "#7bc88f", "#3aab7e"])
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9, "text.color": INK,
        "axes.edgecolor": CARD_BORDER, "axes.linewidth": 0.8, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": BG,
        "axes.facecolor": CARD,
    })
    REPORT_SUPPORT = True
except Exception as e:  # pragma: no cover
    REPORT_SUPPORT = False
    logger.warning("matplotlib/reportlab indisponible - rapport COMEX désactivé (%s)", e)


# ===========================================================================
# Primitives graphiques (portées des maquettes ; signatures inchangées)
# ===========================================================================
def _card_ax(fig, rect, title=None, title_color=None, left=0.07):
    """Carte blanche + axes internes. `left` = marge gauche interne (fraction de la
    largeur) : à augmenter quand le graphique a des libellés d'axe Y longs, sinon
    ils débordent hors de la page."""
    x, y, w, h = rect
    # Ombre douce unique (évite l'effet « escalier / griffe » de l'ancien empilement).
    sh = fig.add_axes([x + 0.002, y - 0.006, w, h])
    sh.axis("off")
    sh.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=sh.transAxes,
                 boxstyle="round,pad=0.005,rounding_size=0.05", fc="#0f172a", ec="none", alpha=0.06))
    fr = fig.add_axes([x, y, w, h])
    fr.axis("off")
    fr.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=fr.transAxes,
                 boxstyle="round,pad=0.005,rounding_size=0.05", fc=CARD, ec=CARD_BORDER, lw=1.1))
    if title:
        fr.add_patch(Rectangle((0.04, 0.905), 0.018, 0.05, transform=fr.transAxes,
                     fc=title_color or GREEN, ec="none"))
        fr.text(0.075, 0.93, title, transform=fr.transAxes, fontsize=9.5,
                fontweight="bold", color=title_color or INK, va="center")
    pad_top = 0.17 if title else 0.06
    right = 0.06
    inner = fig.add_axes([x + w * left, y + h * 0.10, w * (1 - left - right), h * (0.92 - pad_top - 0.06)])
    inner.set_facecolor(CARD)
    return inner


# Tonalités des cartes KPI (fond, bordure, couleur du chiffre, couleur icône) —
# alignées sur la palette du tableau de bord RH web.
_TONES = {
    "neutral": ("#f1f5f9", "#e2e8f0", "#0f766e", "#94a3b8"),
    "emerald": ("#ecfdf5", "#a7f3d0", "#047857", "#34d399"),
    "rose":    ("#fff1f2", "#fecdd3", "#be123c", "#fb7185"),
    "amber":   ("#fffbeb", "#fde68a", "#b45309", "#f59e0b"),
    "violet":  ("#f5f3ff", "#ddd6fe", "#6d28d9", "#a78bfa"),
}


def _kpi_card(fig, rect, value, label, tone="neutral", icon=""):
    """Carte KPI colorée, plate (sans ombre empilée ni barre d'accent saillante)."""
    x, y, w, h = rect
    bg, border, valcol, iconcol = _TONES.get(tone, _TONES["neutral"])
    ax = fig.add_axes([x, y, w, h])
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.01, -0.015), 0.98, 0.985, transform=ax.transAxes,
                 boxstyle="round,pad=0.006,rounding_size=0.12", fc="#0f172a", ec="none", alpha=0.05))
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=ax.transAxes,
                 boxstyle="round,pad=0.006,rounding_size=0.12", fc=bg, ec=border, lw=1.2))
    ax.text(0.085, 0.63, str(value), transform=ax.transAxes, fontsize=19,
            fontweight="bold", color=valcol, va="center")
    if icon:
        ax.text(0.90, 0.68, icon, transform=ax.transAxes, fontsize=10.5,
                color=iconcol, va="center", ha="center")
    for j, ln in enumerate(textwrap.wrap(label, 24)[:2]):
        ax.text(0.085, 0.27 - j * 0.155, ln, transform=ax.transAxes,
                fontsize=7.3, color="#475569", va="center")
    return ax


def _donut(ax, values, labels, colors, center_txt="", center_sub=""):
    ax.pie(values, colors=colors[:len(values)], startangle=90, counterclock=False, radius=0.92,
           wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2.6))
    ax.text(0, 0.10, center_txt, ha="center", va="center", fontsize=16, fontweight="bold", color=INK)
    ax.text(0, -0.18, center_sub, ha="center", va="center", fontsize=7.5, color=MUTED)
    total = sum(values) or 1
    items = [f"{lab}  {v / total * 100:.0f}%" for lab, v in zip(labels, values)]
    handles = [mpatches.Patch(fc=colors[i], label=items[i]) for i in range(len(values))]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False,
              fontsize=7.0, ncol=len(values), labelcolor=INK, handlelength=0.8, handleheight=0.8,
              columnspacing=1.0, handletextpad=0.4)
    ax.set_aspect("equal")


def _hbar(ax, items, color=GREEN, vmax=None, pct=False):
    labels = [i[0] for i in items][::-1]
    vals = [i[1] for i in items][::-1]
    cols = [i[2] if len(i) > 2 else color for i in items][::-1]
    vmax = vmax or (max(vals) * 1.18 if vals else 1)
    n = len(vals)
    ax.barh(range(n), [vmax] * n, color="#eef2f7", height=0.58, ec="none", zorder=1)
    ax.barh(range(n), vals, color=cols, height=0.58, ec="none", zorder=3)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=7.9, color=INK)
    ax.set_xlim(0, vmax)
    for i, v in enumerate(vals):
        if v <= 0:
            continue
        ax.text(v + vmax * 0.015, i, (f"{v}%" if pct else f"{v}"), va="center",
                fontsize=7.6, fontweight="bold", color=INK, zorder=4)
    ax.set_xticks([])
    ax.tick_params(labelsize=7, colors=MUTED, length=0)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)


def _bullet(ax, items, vmax=100, target=80):
    ax.set_xlim(0, vmax)
    ax.set_ylim(-0.6, len(items) - 0.4)
    for i, (name, val) in enumerate(items[::-1]):
        for x0, x1, c in [(0, 50, "#fdecec"), (50, 75, "#fef4e0"), (75, vmax, "#e7f7ee")]:
            ax.barh(i, x1 - x0, left=x0, height=0.60, color=c, ec="none", zorder=1)
        ax.barh(i, val, height=0.22, color=GREEN_D, ec="none", zorder=3)
        ax.plot([target, target], [i - 0.30, i + 0.30], color=INK, lw=2, zorder=4)
        ax.text(-1.5, i, name, ha="right", va="center", fontsize=8, color=INK)
        ax.text(val + 1.2, i, f"{val}", va="center", fontsize=7.6, fontweight="bold", color=GREEN_D, zorder=5)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(labelsize=7, colors=MUTED, length=0)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)


def _taux_par_critere(ax, items, target=70):
    labels = [i[0] for i in items][::-1]
    vals = [i[1] for i in items][::-1]
    cols = [(GREEN if v >= target else (AMBER if v >= 50 else RED)) for v in vals]
    n = len(vals)
    ax.barh(range(n), [100] * n, color="#eef2f7", height=0.58, ec="none", zorder=1)
    ax.barh(range(n), vals, color=cols, height=0.58, ec="none", zorder=3)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=8, color=INK)
    ax.set_xlim(0, 100)
    ax.axvline(target, color=INK, lw=1.2, ls="--", zorder=4)
    for i, v in enumerate(vals):
        ax.text(max(v - 3, 6), i, f"{v}%", va="center", ha="right", fontsize=7.6,
                fontweight="bold", color="white", zorder=5)
    ax.set_xticks([])
    ax.tick_params(labelsize=7, colors=MUTED, length=0)
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)


def _squarify(values, x, y, w, h):
    rects = []

    def rec(vals, x, y, w, h, horiz):
        if not vals:
            return
        if len(vals) == 1:
            rects.append((x, y, w, h))
            return
        half = sum(vals) / 2
        acc, i = 0, 0
        while i < len(vals) - 1 and acc + vals[i] <= half:
            acc += vals[i]
            i += 1
        i = max(i, 1)
        frac = sum(vals[:i]) / sum(vals)
        if horiz:
            rec(vals[:i], x, y, w * frac, h, not horiz)
            rec(vals[i:], x + w * frac, y, w * (1 - frac), h, not horiz)
        else:
            rec(vals[:i], x, y + h * (1 - frac), w, h * frac, not horiz)
            rec(vals[i:], x, y, w, h * (1 - frac), not horiz)
    rec(list(values), x, y, w, h, True)
    return rects


def _treemap(ax, data):
    """data = [(label, value, color)]"""
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    data = [d for d in data if d[1] > 0] or [("—", 1, SLATE)]
    rects = _squarify([d[1] for d in data], 0, 0, 1, 1)
    for (lab, val, col), (x, y, w, h) in zip(data, rects):
        ax.add_patch(FancyBboxPatch((x + 0.006, y + 0.008), w - 0.012, h - 0.016,
                     boxstyle="round,pad=0,rounding_size=0.012", fc=col, ec="white", lw=2.4))
        if w * h > 0.04:
            ax.text(x + w / 2, y + h / 2 + 0.035, lab, ha="center", va="center",
                    fontsize=min(11, 5.5 + 26 * w * h), color="white", fontweight="bold")
            ax.text(x + w / 2, y + h / 2 - 0.055, f"{val}", ha="center", va="center",
                    fontsize=min(10, 4.5 + 20 * w * h), color="white", alpha=0.92)
        elif w * h > 0.012:
            ax.text(x + w / 2, y + h / 2, f"{lab}\n{val}", ha="center", va="center", fontsize=5.8, color="white")


def _heatmap(ax, data, rows, cols):
    data = np.array(data, dtype=float)
    ax.imshow(data, cmap=HEAT_CMAP, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, fontsize=7, rotation=18, ha="right")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows, fontsize=7.6)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_xticks(np.arange(-.5, len(cols), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(rows), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2.5)
    ax.tick_params(which="minor", length=0)
    for i in range(len(rows)):
        for j in range(len(cols)):
            v = data[i][j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.2,
                    color="white" if (v < 38 or v > 80) else INK, fontweight="bold")
    for s in ax.spines.values():
        s.set_visible(False)


# ===========================================================================
# Composition des panneaux pleine page
# ===========================================================================
def _new_panel(title, subtitle=""):
    fig = plt.figure(figsize=(7.6, 10.0), dpi=150)
    fig.patch.set_facecolor(BG)
    acc = fig.add_axes([0.045, 0.957, 0.016, 0.020])
    acc.axis("off")
    acc.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=acc.transAxes,
                  boxstyle="round,pad=0,rounding_size=0.35", fc=GREEN, ec="none"))
    fig.text(0.072, 0.963, title, fontsize=16, fontweight="bold", color=INK, va="center")
    if subtitle:
        fig.text(0.072, 0.940, subtitle, fontsize=8.6, color=MUTED, va="center")
    sep = fig.add_axes([0.0, 0.927, 1.0, 0.002])
    sep.axis("off")
    sep.axhline(0.5, color="#e2e8f1", lw=1)
    return fig


def _text_card(fig, rect, title=None, tcolor=None):
    x, y, w, h = rect
    sh = fig.add_axes([x + 0.002, y - 0.006, w, h])
    sh.axis("off")
    sh.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=sh.transAxes,
                 boxstyle="round,pad=0.005,rounding_size=0.05", fc="#0f172a", ec="none", alpha=0.06))
    fr = fig.add_axes([x, y, w, h])
    fr.axis("off")
    fr.set_xlim(0, 1)
    fr.set_ylim(0, 1)
    fr.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=fr.transAxes,
                 boxstyle="round,pad=0.005,rounding_size=0.05", fc=CARD, ec=CARD_BORDER, lw=1.1))
    if title:
        fr.add_patch(Rectangle((0.028, 0.90), 0.011, 0.07, transform=fr.transAxes, fc=tcolor or GREEN, ec="none"))
        fr.text(0.055, 0.935, title, transform=fr.transAxes, fontsize=10, fontweight="bold", color=INK, va="center")
    return fr


def _kpi_row(fig, cards, y, w=0.292, h=0.075, x0=0.045, gap=0.017):
    x = x0
    for c in cards:
        _kpi_card(fig, (x, y, w, h), *c)
        x += w + gap


def _numbered(fr, items, y0=0.84, dy=0.30, fs=9.8, width=90):
    for i, (c, txt) in enumerate(items):
        y = y0 - i * dy
        fr.scatter([0.05], [y], s=210, color=c, zorder=3, edgecolor="white", lw=1)
        fr.text(0.05, y, str(i + 1), ha="center", va="center", fontsize=8.5, color="white", fontweight="bold", zorder=4)
        for j, ln in enumerate(textwrap.wrap(txt, width) or [txt]):
            fr.text(0.105, y - j * 0.058, ln, va="center", fontsize=fs, color=INK)


def _dotted(fr, items, y0=0.82, dy=0.20, fs=8.6, width=88):
    for i, txt in enumerate(items):
        y = y0 - i * dy
        fr.scatter([0.04], [y], s=42, color=GREEN, zorder=3)
        for j, ln in enumerate(textwrap.wrap(txt, width) or [txt]):
            fr.text(0.085, y - j * 0.052, ln, va="center", fontsize=fs, color=INK)


def _ia_box(fig, rect, text):
    x, y, w, h = rect
    ax = fig.add_axes([x, y, w, h])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, transform=ax.transAxes,
                 boxstyle="round,pad=0.005,rounding_size=0.10", fc="#e9f7f1", ec=GREEN, lw=1.2))
    ax.add_patch(Rectangle((0.0, 0.1), 0.005, 0.8, transform=ax.transAxes, fc=GREEN, ec="none"))
    ax.text(0.018, 0.72, "✦ Synthèse", fontsize=8.8, fontweight="bold", color=GREEN_D, va="center")
    ax.text(0.018, 0.33, text, fontsize=8.3, color=INK, va="center", wrap=True)


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=fig.get_facecolor(), pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf


# ===========================================================================
# Préparation des données réelles
# ===========================================================================
def _axis_color(x):
    return RED if x.get("over_concentrated") else (SLATE if x.get("orphan") else GREEN)


def _derive(a):
    vol = a.get("volumetry") or {}
    total, analyzed = int(vol.get("total") or 0), int(vol.get("analyzed") or 0)
    sr = a.get("smart_rate") or {}
    smart_ok = int(sr.get("ok") or 0)
    avg = a.get("avg_scores") or {}
    bp = a.get("blocking_points") or []
    fmap = {r.get("criteria"): int(r.get("failures") or 0) for r in bp}
    ac = a.get("axis_coverage") or {}
    axes = ac.get("axes") or []
    al_dist = {r.get("level", ""): int(r.get("count") or 0) for r in (a.get("alignment_distribution") or [])}
    faible = next((v for k, v in al_dist.items() if k.lower().startswith("faible")), 0)
    thr = a.get("thresholds") or {}
    smart_thr = thr.get("smart") or 80
    ent = a.get("entity_comparison") or []
    mgr = a.get("manager_comparison") or []
    return {
        "total": total, "analyzed": analyzed,
        "smart_rate": round(float(sr.get("rate") or 0)), "smart_ok": smart_ok,
        "avg_smart": round(float(avg.get("avg_smart") or 0)),
        "avg_align": round(float(avg.get("avg_alignment") or 0)),
        "a_ajuster": max(0, int(sr.get("total") or 0) - smart_ok),
        "sans_kpi": fmap.get("M - Mesurable", 0), "sans_echeance": fmap.get("T - Temporel", 0),
        "flous": fmap.get("S - Spécifique", 0),
        "worst": bp[0].get("criteria") if bp else "—",
        "best": min(bp, key=lambda r: int(r.get("failures") or 0)).get("criteria") if bp else "—",
        "blocking": bp,
        "crit": {k: round(float(avg.get(f"avg_{k.lower()}") or 0) * 100) for k in ("S", "M", "A", "R", "T")},
        "axes": axes, "orphans": [x for x in axes if x.get("orphan")],
        "over": [x for x in axes if x.get("over_concentrated")],
        "covered": len([x for x in axes if not x.get("orphan")]), "naxes": len(axes),
        "total_aligned": int(ac.get("total_aligned") or 0),
        "over_threshold": ac.get("over_concentration_threshold") or 40,
        "low_confidence": int((a.get("low_confidence") or {}).get("count") or 0),
        "validated": int((a.get("global_stats") or {}).get("validated") or 0),
        "align_rate": round(float((a.get("alignment_rate") or {}).get("rate") or 0)),
        "smart_thr": smart_thr, "faible_align": faible,
        "alignment_distribution": a.get("alignment_distribution") or [],
        "entities": ent, "managers": mgr,
        "entities_below": len([e for e in ent if float(e.get("avg_smart") or 0) < smart_thr]),
    }


def _entity_axis(objective_rows, axes, max_entities=5):
    """Matrice alignement moyen entité × axe (depuis les top_matches), ou None."""
    titles = {str(a.get("axis_id")): (a.get("axis_title") or str(a.get("axis_id")))[:9] for a in axes}
    by_ent = {}
    ent_count = {}
    for o in objective_rows:
        ent = (o.get("entity") or "").strip() or "Non spécifié"
        raw = o.get("alignment_analysis")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = None
        if not isinstance(raw, dict):
            continue
        matches = [m for m in (raw.get("top_matches") or []) if isinstance(m, dict) and m.get("objective_id") is not None]
        if not matches:
            continue
        aid = str(max(matches, key=lambda m: m.get("score") or 0).get("objective_id"))
        if aid not in titles:
            continue
        score = float(o.get("alignment_score") or 0)
        by_ent.setdefault(ent, {}).setdefault(aid, []).append(score)
        ent_count[ent] = ent_count.get(ent, 0) + 1
    if not by_ent:
        return None
    top_ents = [e for e, _ in sorted(ent_count.items(), key=lambda kv: kv[1], reverse=True)[:max_entities]]
    axis_ids = [a for a in titles if any(a in by_ent[e] for e in top_ents)][:5]
    if not axis_ids:
        return None
    matrix = [[(sum(by_ent[e].get(aid, [])) / len(by_ent[e][aid]) if by_ent[e].get(aid) else 0)
               for aid in axis_ids] for e in top_ents]
    return matrix, [e[:11] for e in top_ents], [titles[a] for a in axis_ids]


# ===========================================================================
# Panneaux
# ===========================================================================
def _p_synthese(d):
    f = _new_panel("1.  Synthèse exécutive",
                   "Vue suffisante pour comprendre l'état global des objectifs")
    pct = round(d["analyzed"] / d["total"] * 100) if d["total"] else 0
    _ia_box(f, (0.045, 0.860, 0.91, 0.056),
            f"{d['analyzed']} objectifs analysés sur {d['total']} importés ({pct} %). "
            f"Taux d'objectifs SMART : {d['smart_rate']} % (cible {d['smart_thr']} %). "
            f"Critère le plus souvent non validé : {d['worst']}.")
    # Les 8 KPI EXACTEMENT identiques au tableau de bord RH (même source get_analytics,
    # mêmes libellés, mêmes valeurs) : le rapport COMEX = photo fidèle du dashboard.
    _kpi_row(f, [(f"{d['analyzed']} / {d['total']}", "Objectifs analysés", "neutral", "▤"),
                 (f"{d['avg_smart']} %", "Score SMART moyen", "neutral", "★"),
                 (f"{d['avg_align']} %", "Alignement moyen", "neutral", "◆"),
                 (f"{d['validated']}", "Objectifs validés", "neutral", "●")],
             y=0.775, w=0.218, gap=0.012)
    _kpi_row(f, [(f"{d['a_ajuster']}", "Objectifs à ajuster", "rose", "!"),
                 (f"{d['smart_rate']} %", "Taux d'objectifs SMART", "emerald", "◎"),
                 (f"{d['align_rate']} %", "Alignement stratégique fort", "amber", "◇"),
                 (f"{d['low_confidence']}", "Faible confiance IA", "violet", "?")],
             y=0.672, w=0.218, gap=0.012)
    fr = _text_card(f, (0.045, 0.075, 0.91, 0.520), "3 points d'attention (constats factuels)", RED)
    pts = []
    if d["worst"] != "—":
        wf = max(d["sans_kpi"], d["sans_echeance"], d["flous"])
        pts.append((RED, f"Critère « {d['worst']} » le plus souvent non validé : {wf} objectif(s) concerné(s)."))
    for x in d["orphans"][:1]:
        pts.append((AMBER, f"Axe « {x.get('axis_title','')} » sans aucun objectif rattaché (axe orphelin)."))
    for x in d["over"][:1]:
        pts.append((AMBER, f"« {x.get('axis_title','')} » capte {x.get('share_pct',0)} % des objectifs (seuil {d['over_threshold']} %)."))
    if not pts:
        pts.append((GREEN, "Aucun point d'attention majeur sur le périmètre analysé."))
    _numbered(fr, pts[:3])
    return _png(f)


def _p_pilotage(d, ent_axis):
    f = _new_panel("2.  Pilotage stratégique — couverture des axes",
                   f"Répartition des {d['total_aligned']} objectifs rattachés à un axe stratégique")
    ax = _card_ax(f, (0.045, 0.560, 0.45, 0.345), "Poids des axes — treemap (rouge = sur-concentré)")
    _treemap(ax, [(x.get("axis_title", "")[:10], int(x.get("count") or 0), _axis_color(x)) for x in d["axes"]])
    ax = _card_ax(f, (0.505, 0.560, 0.45, 0.345), "Couverture par axe (% des objectifs)", left=0.30)
    _hbar(ax, [(x.get("axis_title", "")[:14], round(float(x.get("share_pct") or 0)), _axis_color(x)) for x in d["axes"][:7]],
          pct=True, vmax=max(50, d["over_threshold"] + 10))
    ax.axvline(d["over_threshold"], color=INK, lw=1.2, ls="--")
    if ent_axis:
        matrix, rows, cols = ent_axis
        ax = _card_ax(f, (0.045, 0.230, 0.55, 0.305), "Alignement moyen par entité × axe")
        _heatmap(ax, matrix, rows, cols)
    else:
        fr = _text_card(f, (0.045, 0.230, 0.55, 0.305), "Alignement par entité × axe")
        fr.text(0.5, 0.5, "Données insuffisantes\n(axes non rattachés)", ha="center", va="center", fontsize=9, color=MUTED)
    ax = _card_ax(f, (0.61, 0.230, 0.345, 0.305), "Niveaux d'alignement")
    dist = d["alignment_distribution"] or [{"level": "—", "count": 1}]
    _donut(ax, [int(r.get("count") or 0) for r in dist], [r.get("level", "")[:6] for r in dist],
           [GREEN, AMBER, RED], f"{d['avg_align']} %", "alignement")
    fr = _text_card(f, (0.045, 0.050, 0.91, 0.155), "Constats", GREEN_D)
    cons = []
    for x in d["orphans"][:1]:
        cons.append(f"Axe orphelin : « {x.get('axis_title','')} » ne reçoit aucun objectif.")
    for x in d["over"][:1]:
        cons.append(f"Sur-concentration : « {x.get('axis_title','')} » capte {x.get('share_pct',0)} % des objectifs (seuil {d['over_threshold']} %).")
    cons.append(f"{d['covered']} axe(s) couvert(s) sur {d['naxes']}.")
    _dotted(fr, cons[:3], y0=0.80, dy=0.27, fs=8.2)
    return _png(f)


def _p_qualite(d):
    f = _new_panel("3.  Qualité SMART",
                   "Niveau de conformité des objectifs aux 5 critères de la méthode SMART")
    _kpi_row(f, [(f"{d['sans_kpi']}", "Objectifs sans KPI", "amber", "M"),
                 (f"{d['sans_echeance']}", "Sans échéance", "amber", "T"),
                 (f"{d['flous']}", "Objectifs flous", "amber", "S"),
                 (f"{d['avg_smart']} / 100", "Score SMART moyen", "emerald", "★")],
             y=0.815, w=0.218, gap=0.013)
    ax = _card_ax(f, (0.045, 0.430, 0.55, 0.340), "Taux de conformité par critère SMART (cible 70 %)")
    _taux_par_critere(ax, [("S", d["crit"]["S"]), ("M", d["crit"]["M"]), ("A", d["crit"]["A"]),
                           ("R", d["crit"]["R"]), ("T", d["crit"]["T"])], target=70)
    ax = _card_ax(f, (0.620, 0.430, 0.335, 0.340), "Nombre d'échecs par critère")
    pal = [RED, "#f87171", AMBER, "#fbbf24", "#a3e635"]
    _hbar(ax, [(r.get("criteria", ""), int(r.get("failures") or 0), pal[i % len(pal)]) for i, r in enumerate(d["blocking"])])
    ax = _card_ax(f, (0.045, 0.070, 0.43, 0.330), "Objectifs SMART / non-SMART")
    _donut(ax, [d["smart_ok"], d["a_ajuster"]], ["Conformes", "À retravailler"],
           [GREEN, "#fca5a5"], f"{d['smart_rate']} %", "conformes")
    fr = _text_card(f, (0.500, 0.070, 0.455, 0.330), "Lecture rapide", GREEN_D)
    _dotted(fr, [
        f"Point fort : critère « {d['best']} » ({d['crit'].get(d['best'][:1], '')} %).",
        f"Point faible : critère « {d['worst']} » ({d['crit'].get(d['worst'][:1], '')} %).",
        f"{d['a_ajuster']} objectif(s) à retravailler pour atteindre le seuil SMART de {d['smart_thr']} %.",
    ], y0=0.80, dy=0.235, fs=8.4, width=46)
    return _png(f)


def _p_comparatifs(d):
    f = _new_panel("4.  Comparatifs par périmètre",
                   "Lecture comparative, sans objectif de sanction : repérer où un appui serait le plus utile")
    ent = sorted(d["entities"], key=lambda e: float(e.get("avg_smart") or 0), reverse=True)[:6]
    ax = _card_ax(f, (0.045, 0.470, 0.91, 0.400), "Score SMART moyen par entité (cible 80)", left=0.19)
    if ent:
        _bullet(ax, [((e.get("entity") or "—")[:18], round(float(e.get("avg_smart") or 0))) for e in ent])
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "Aucune entité renseignée", ha="center", va="center", fontsize=9, color=MUTED)
    mgr = sorted(d["managers"], key=lambda m: float(m.get("avg_smart") or 0), reverse=True)
    top = mgr[:3]
    flop = mgr[-3:] if len(mgr) > 3 else []
    sel = top + [m for m in flop if m not in top]
    ax = _card_ax(f, (0.045, 0.070, 0.91, 0.370), "Managers — Top 3 / Flop 3 (score SMART moyen)", left=0.17)
    if sel:
        rows = []
        for m in sel:
            v = round(float(m.get("avg_smart") or 0))
            rows.append(((m.get("manager") or "—")[:22], v, GREEN if v >= d["smart_thr"] else (AMBER if v >= 50 else RED)))
        _hbar(ax, rows, vmax=100, pct=True)
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "Aucun manager renseigné", ha="center", va="center", fontsize=9, color=MUTED)
    return _png(f)


def _p_attention(d):
    f = _new_panel("5.  Points d'attention",
                   "Signaux à surveiller, formulés en constats — chaque chiffre renvoie aux listes dans l'app")
    _kpi_row(f, [(f"{d['a_ajuster']}", "Objectifs à ajuster", "rose", "!"),
                 (f"{d['faible_align']}", "Objectifs faiblement alignés", "amber", "◇"),
                 (f"{d['low_confidence']}", "Analyses à faible confiance IA", "violet", "?")], y=0.780)
    _kpi_row(f, [(f"{len(d['orphans'])}", "Axe(s) stratégique(s) orphelin(s)", "rose", "○"),
                 (f"{d['entities_below']}", f"Entités sous la cible ({d['smart_thr']} %)", "amber", "▤"),
                 (f"{len(d['over'])}", "Axe(s) sur-concentré(s)", "rose", "▣")], y=0.692)
    ent = sorted(d["entities"], key=lambda e: float(e.get("avg_smart") or 0))[:5]
    ax = _card_ax(f, (0.045, 0.330, 0.55, 0.300), "Périmètres les plus éloignés de la cible (score SMART)", left=0.27)
    if ent:
        rows = []
        for e in ent:
            v = round(float(e.get("avg_smart") or 0))
            rows.append(((e.get("entity") or "—")[:14], v, RED if v < 50 else (AMBER if v < d["smart_thr"] else GREEN)))
        _hbar(ax, rows, vmax=100, pct=True)
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "Aucune entité renseignée", ha="center", va="center", fontsize=9, color=MUTED)
    fr = _text_card(f, (0.620, 0.330, 0.335, 0.300), "Lecture", GREEN_D)
    lect = []
    if d["worst"] != "—":
        lect.append(f"Critère « {d['worst']} » fréquemment non validé.")
    for x in d["orphans"][:1]:
        lect.append(f"Axe « {x.get('axis_title','')[:16]} » orphelin.")
    lect.append(f"{d['entities_below']} entité(s) sous la cible.")
    _dotted(fr, lect[:4], y0=0.80, dy=0.255, fs=8.2, width=30)
    fr = _text_card(f, (0.045, 0.055, 0.91, 0.215), "Constat de synthèse", RED)
    _syn = (f"{d['a_ajuster']} objectif(s) à ajuster et {d['faible_align']} objectif(s) faiblement "
            f"alignés constituent les principaux leviers d'amélioration de la campagne.")
    for j, ln in enumerate(textwrap.wrap(_syn, 98)):
        fr.text(0.04, 0.60 - j * 0.24, ln, fontsize=9, color=INK, va="center")
    return _png(f)


def _p_constats(d):
    f = _new_panel("6.  Synthèse des constats   ·   7.  Annexes",
                   "Récapitulatif observationnel — les décisions restent prises par les personnes habilitées")
    fr = _text_card(f, (0.045, 0.470, 0.91, 0.400), "Synthèse des constats", GREEN_D)
    _dotted(fr, [
        f"Taux d'objectifs SMART : {d['smart_rate']} % (cible {d['smart_thr']} %).",
        f"Critère le plus souvent non validé : « {d['worst']} ».",
        f"Alignement stratégique moyen : {d['avg_align']} %.",
        f"Couverture des axes : {d['covered']}/{d['naxes']} ({len(d['orphans'])} orphelin(s), {len(d['over'])} sur-concentré(s)).",
        f"{d['a_ajuster']} objectif(s) à ajuster ; {d['low_confidence']} analyse(s) à relire (faible confiance IA).",
    ], y0=0.83, dy=0.165, fs=8.8)
    fr = _text_card(f, (0.045, 0.130, 0.91, 0.310), "Annexes — disponibles sur demande auprès de la RH", SKY)
    _dotted(fr, [
        "Liste détaillée des objectifs à ajuster (sans KPI, sans échéance, flous, désalignés).",
        "Propositions de reformulation IA (avant / après), toujours soumises à validation humaine.",
        "Méthodologie de calcul des scores SMART et d'alignement, et seuils appliqués sur la période.",
    ], y0=0.78, dy=0.26, fs=8.8)
    f.text(0.5, 0.075, "Confidentiel — diffusion restreinte   ·   Éléments fournis à titre d'aide à la décision.",
           ha="center", fontsize=8.5, color=MUTED, style="italic")
    return _png(f)


# ===========================================================================
# Assemblage du PDF
# ===========================================================================
def generate(analytics, objective_rows=None, meta=None) -> StreamingResponse:
    """Construit le rapport COMEX (PDF portrait) à partir des agrégats RH."""
    if not REPORT_SUPPORT:
        raise HTTPException(status_code=500,
                            detail="matplotlib/reportlab non installés. Exécutez: pip install -r requirements.txt")
    meta = meta or {}
    d = _derive(analytics)
    when = meta.get("generated_at") or datetime.now().strftime("%d/%m/%Y %H:%M")
    period = meta.get("period") or "Toutes périodes"
    scope = meta.get("scope") or "Groupe BMCI — toutes entités"

    ss = getSampleStyleSheet()
    cap = ParagraphStyle("cap", parent=ss["Normal"], fontSize=8, leading=10,
                         textColor=rl.HexColor(MUTED), alignment=1, spaceBefore=1, spaceAfter=6)
    story = []

    if d["analyzed"] == 0:
        story += [Spacer(1, 5 * cm),
                  Paragraph("Rapport de pilotage des objectifs — Direction / COMEX",
                            ParagraphStyle("t", parent=ss["Title"], fontSize=20,
                                           textColor=rl.HexColor(GREEN_D), alignment=1)),
                  Spacer(1, 1 * cm),
                  Paragraph("Données insuffisantes : aucun objectif analysé sur le périmètre sélectionné. "
                            "Importez et analysez des objectifs avant de générer ce rapport.", cap)]
        return _assemble(story, when, period, scope)

    ent_axis = None
    if objective_rows and d["axes"]:
        try:
            ent_axis = _entity_axis(objective_rows, d["axes"])
        except Exception as e:  # pragma: no cover
            logger.warning("entity×axis non calculable (%s)", e)

    # Couverture
    story += [
        Spacer(1, 5.2 * cm),
        Paragraph("Rapport de pilotage des objectifs",
                  ParagraphStyle("t1", parent=ss["Title"], fontSize=25, textColor=rl.HexColor(GREEN_D), alignment=1, spaceAfter=6)),
        Paragraph("Synthèse SMART &amp; alignement stratégique — Direction / COMEX",
                  ParagraphStyle("t2", parent=ss["Normal"], fontSize=13, textColor=rl.HexColor(MUTED), alignment=1)),
        Spacer(1, 26),
        Table([[Paragraph(f"<b>Période</b><br/>{period}", cap),
                Paragraph(f"<b>Périmètre</b><br/>{scope}", cap),
                Paragraph(f"<b>Édité le</b><br/>{when}", cap)]],
              colWidths=[6.0 * cm] * 3, style=TableStyle([
                  ("BOX", (0, 0), (-1, -1), 0.6, rl.HexColor("#dbe3ea")),
                  ("INNERGRID", (0, 0), (-1, -1), 0.6, rl.HexColor("#dbe3ea")),
                  ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                  ("ALIGN", (0, 0), (-1, -1), "CENTER")])),
        Spacer(1, 60),
        Paragraph("Confidentiel — diffusion restreinte",
                  ParagraphStyle("cf", parent=ss["Normal"], fontSize=11, textColor=rl.HexColor(RED_BMCI), alignment=1)),
        Paragraph("Document préparé par la RH. La Direction ne se connecte pas à l'application.", cap),
        PageBreak(),
    ]

    panels = [_p_synthese(d), _p_pilotage(d, ent_axis), _p_qualite(d),
              _p_comparatifs(d), _p_attention(d), _p_constats(d)]
    L = 1.0 * cm
    img_w = A4[0] - 2 * L
    for buf in panels:
        story.append(Image(buf, width=img_w, height=img_w * 10.0 / 7.6))
        story.append(PageBreak())

    return _assemble(story, when, period, scope)


def _assemble(story, when, period, scope):
    output = io.BytesIO()
    L = 1.0 * cm

    def on_page(canvas, doc):
        canvas.saveState()
        if doc.page == 1:
            canvas.setFillColor(rl.HexColor(RED_BMCI))
            canvas.rect(0, A4[1] - 3.4 * cm, A4[0], 3.4 * cm, fill=1, stroke=0)
            canvas.setFillColor(rl.white)
            canvas.setFont("Helvetica-Bold", 26)
            canvas.drawString(2 * cm, A4[1] - 2.1 * cm, "BMCI")
            canvas.setFont("Helvetica", 12)
            canvas.drawString(2 * cm, A4[1] - 2.8 * cm, "Projet Smart Objectif — Pilotage des objectifs")
        else:
            canvas.setFillColor(rl.HexColor(GREEN_D))
            canvas.setFont("Helvetica-Bold", 8.5)
            canvas.drawString(L, A4[1] - 0.85 * cm, "BMCI Smart Objectif — Rapport Direction / COMEX")
            canvas.setFillColor(rl.HexColor(RED_BMCI))
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(A4[0] - L, A4[1] - 0.85 * cm, "Confidentiel")
        canvas.setFillColor(rl.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(L, 0.75 * cm, "Confidentiel - diffusion restreinte")
        canvas.drawRightString(A4[0] - L, 0.75 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = BaseDocTemplate(output, pagesize=A4, leftMargin=L, rightMargin=L,
                          topMargin=1.25 * cm, bottomMargin=1.15 * cm,
                          title="BMCI - Rapport Direction / COMEX")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")
    doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=on_page)])
    doc.build(story)
    output.seek(0)
    filename = f"Rapport_COMEX_BMCI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(output, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})
