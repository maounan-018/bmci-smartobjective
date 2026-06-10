#!/usr/bin/env python3
"""
services/excel_import_service.py — Pipeline d'import Excel intelligent.

RÔLE
    Détection automatique des colonnes (objectif / description) dans des fichiers
    Excel désordonnés, extraction/nettoyage des objectifs, analyse IA en lot et
    génération d'un Excel enrichi des résultats.

    Fonctions :
      - ExcelColumnDetector       : heuristiques de scoring des colonnes
      - scan_excel_file           : exploration de toutes les feuilles
      - extract_objectives_from_excel : extraction + déduplication
      - build_ai_payload          : préparation du payload IA
      - analyze_objectives_batch  : analyse SMART + alignement en lot
      - create_result_excel       : Excel enrichi (structure d'origine conservée)

EMPLACEMENT MVC
    Couche "services" : logique d'import/analyse, sans route HTTP.
"""

import re
import io
import json
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any
from difflib import SequenceMatcher

from fastapi import HTTPException

from app.services.ai_service import analyze_smart_internal, analyze_alignment_internal
from app.database.session import db_session
from app.repositories import company_objective_repository, analysis_repository

# openpyxl est optionnel : l'import échoue proprement si absent.
try:
    import openpyxl
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    EXCEL_SUPPORT = True
except Exception as e:  # pragma: no cover
    EXCEL_SUPPORT = False
    print(f"[WARNING] openpyxl indisponible - import Excel limité ({e})")


class ExcelColumnDetector:
    """Détecteur intelligent de colonnes pour fichiers Excel désordonnés."""

    OBJECTIVE_KEYWORDS = [
        'objectif', 'objectifs', 'objective', 'objectives', 'goal', 'goals',
        'strategic goal', 'objectif stratégique', 'objectifs stratégiques',
        'titre', 'title', 'intitulé', 'libellé', 'nom', 'name',
        'kpi', 'indicateur', 'target', 'cible', 'but', 'finalité'
    ]

    DESCRIPTION_KEYWORDS = [
        'description', 'desc', 'détail', 'détails', 'detail', 'details',
        'commentaire', 'commentaires', 'comment', 'comments', 'note', 'notes',
        'justification', 'explication', 'explanation', 'contexte', 'context',
        'précision', 'information', 'info', 'remarque', 'observation'
    ]

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalise un texte (minuscules, sans accents) pour la comparaison."""
        if not text:
            return ""
        text = str(text).lower().strip()
        replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
                        'à': 'a', 'â': 'a', 'ä': 'a',
                        'ù': 'u', 'û': 'u', 'ü': 'u',
                        'î': 'i', 'ï': 'i', 'ô': 'o', 'ö': 'o',
                        'ç': 'c', '_': ' ', '-': ' '}
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """Similarité (ratio) entre deux textes."""
        return SequenceMatcher(None, text1, text2).ratio()

    @classmethod
    def score_column_as_objective(cls, col_name: str, sample_values: List[str]) -> float:
        """Score une colonne comme potentielle colonne d'objectifs (0-1)."""
        score = 0.0
        normalized_name = cls.normalize_text(col_name)

        for keyword in cls.OBJECTIVE_KEYWORDS:
            if keyword in normalized_name:
                score += 0.5
                break
            similarity = cls.calculate_similarity(normalized_name, keyword)
            if similarity > 0.7:
                score += 0.3
                break

        if sample_values:
            avg_length = sum(len(str(v)) for v in sample_values if v) / max(len(sample_values), 1)
            if 10 <= avg_length <= 200:
                score += 0.3
            elif avg_length > 200:
                score += 0.1

            action_words = ['augmenter', 'réduire', 'améliorer', 'développer', 'atteindre',
                            'optimiser', 'renforcer', 'mettre en place', 'déployer', 'implémenter',
                            'increase', 'reduce', 'improve', 'develop', 'achieve', 'implement']
            for val in sample_values[:5]:
                val_lower = cls.normalize_text(str(val))
                if any(word in val_lower for word in action_words):
                    score += 0.1
                    break

        return min(score, 1.0)

    @classmethod
    def score_column_as_description(cls, col_name: str, sample_values: List[str]) -> float:
        """Score une colonne comme potentielle colonne de description (0-1)."""
        score = 0.0
        normalized_name = cls.normalize_text(col_name)

        for keyword in cls.DESCRIPTION_KEYWORDS:
            if keyword in normalized_name:
                score += 0.5
                break
            similarity = cls.calculate_similarity(normalized_name, keyword)
            if similarity > 0.7:
                score += 0.3
                break

        if sample_values:
            avg_length = sum(len(str(v)) for v in sample_values if v) / max(len(sample_values), 1)
            if avg_length > 50:
                score += 0.3
            elif avg_length > 100:
                score += 0.4

        return min(score, 1.0)


def scan_excel_file(wb) -> Dict[str, Any]:
    """Scanne un classeur Excel et identifie la meilleure feuille/colonne d'objectifs."""
    scan_result = {
        "sheets": [],
        "total_sheets": len(wb.sheetnames),
        "best_sheet": None,
        "best_objective_column": None,
        "best_description_column": None
    }

    best_obj_score = 0
    best_desc_score = 0

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        sheet_info = {
            "name": sheet_name,
            "columns": [],
            "row_count": ws.max_row,
            "col_count": ws.max_column,
            "detected_objective_col": None,
            "detected_description_col": None
        }

        headers = []
        for col_idx in range(1, ws.max_column + 1):
            cell_value = ws.cell(row=1, column=col_idx).value
            headers.append(str(cell_value) if cell_value else f"Column_{col_idx}")

        for col_idx, header in enumerate(headers, 1):
            sample_values = []
            for row_idx in range(2, min(12, ws.max_row + 1)):
                cell_value = ws.cell(row=row_idx, column=col_idx).value
                if cell_value:
                    sample_values.append(str(cell_value))

            obj_score = ExcelColumnDetector.score_column_as_objective(header, sample_values)
            desc_score = ExcelColumnDetector.score_column_as_description(header, sample_values)

            col_info = {
                "index": col_idx,
                "name": header,
                "sample_values": sample_values[:3],
                "objective_score": round(obj_score, 2),
                "description_score": round(desc_score, 2)
            }
            sheet_info["columns"].append(col_info)

            if obj_score > best_obj_score:
                best_obj_score = obj_score
                scan_result["best_sheet"] = sheet_name
                scan_result["best_objective_column"] = {
                    "sheet": sheet_name, "index": col_idx,
                    "name": header, "score": round(obj_score, 2)
                }
                sheet_info["detected_objective_col"] = col_idx

            if desc_score > best_desc_score:
                best_desc_score = desc_score
                scan_result["best_description_column"] = {
                    "sheet": sheet_name, "index": col_idx,
                    "name": header, "score": round(desc_score, 2)
                }
                sheet_info["detected_description_col"] = col_idx

        scan_result["sheets"].append(sheet_info)

    return scan_result


def extract_objectives_from_excel(
    wb,
    objective_col: Optional[int] = None,
    description_col: Optional[int] = None,
    sheet_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Extrait, nettoie et déduplique les objectifs d'un classeur Excel."""
    if objective_col is None:
        scan = scan_excel_file(wb)
        if scan["best_objective_column"]:
            objective_col = scan["best_objective_column"]["index"]
            sheet_name = scan["best_objective_column"]["sheet"]
        if scan["best_description_column"]:
            description_col = scan["best_description_column"]["index"]

    if objective_col is None:
        raise ValueError("Impossible de détecter la colonne des objectifs. Vérifiez la structure du fichier.")

    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    objectives = []
    seen_titles = set()

    for row_idx in range(2, ws.max_row + 1):
        title_cell = ws.cell(row=row_idx, column=objective_col).value

        if not title_cell:
            continue

        title = str(title_cell).strip()
        title = re.sub(r'\s+', ' ', title).strip()

        if not title or len(title) < 3:
            continue

        title_lower = title.lower()
        if title_lower in seen_titles:
            continue
        seen_titles.add(title_lower)

        description = ""
        if description_col:
            desc_cell = ws.cell(row=row_idx, column=description_col).value
            if desc_cell:
                description = re.sub(r'\s+', ' ', str(desc_cell).strip())

        objectives.append({
            "objective_id": len(objectives) + 1,
            "title": title,
            "description": description,
            "origin": {
                "sheet_name": ws.title,
                "row_index": row_idx,
                "objective_col": objective_col,
                "description_col": description_col
            }
        })

    return objectives


def build_ai_payload(objectives: List[Dict[str, Any]]) -> str:
    """Construit le payload JSON ordonné à envoyer au modèle IA."""
    payload = {
        "total_objectives": len(objectives),
        "objectives": [
            {"id": obj["objective_id"], "title": obj["title"], "description": obj["description"]}
            for obj in objectives
        ]
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analyze_objectives_batch(objectives: List[Dict[str, Any]], company_objectives: List[Dict]) -> List[Dict[str, Any]]:
    """Analyse un lot d'objectifs (SMART + alignement), IDs et ordre préservés."""
    results = []

    for obj in objectives:
        try:
            smart_result = analyze_smart_internal(obj["title"], obj["description"])

            alignment_result = {"alignment_score": 0, "top_matches": [], "gaps": []}
            if company_objectives:
                alignment_result = analyze_alignment_internal(obj["title"], company_objectives)

            smart_score = (
                (1 if smart_result.get('S') else 0) +
                (1 if smart_result.get('M') else 0) +
                (1 if smart_result.get('A') else 0) +
                (1 if smart_result.get('R') else 0) +
                (1 if smart_result.get('T') else 0)
            ) / 5 * 100

            align_score = alignment_result.get('alignment_score', 0)
            if align_score >= 70:
                alignment_text = "Fort"
            elif align_score >= 40:
                alignment_text = "Moyen"
            else:
                alignment_text = "Faible"

            issues = smart_result.get('issues', [])
            recommendations = [issue.get('fix', issue.get('suggestion', '')) for issue in issues[:3] if issue]

            results.append({
                "objective_id": obj["objective_id"],
                "title": obj["title"],
                "description": obj["description"],
                "origin": obj["origin"],
                "analysis": {
                    "smart_score": round(smart_score, 1),
                    "alignment_score": align_score,
                    "alignment_text": alignment_text,
                    "s_score": 1 if smart_result.get('S') else 0,
                    "m_score": 1 if smart_result.get('M') else 0,
                    "a_score": 1 if smart_result.get('A') else 0,
                    "r_score": 1 if smart_result.get('R') else 0,
                    "t_score": 1 if smart_result.get('T') else 0,
                    "issues_count": len(issues),
                    "top_issue": issues[0].get('problem', '') if issues else '',
                    "recommendations": recommendations,
                    "risks_or_gaps": alignment_result.get('gaps', []),
                    "rewrite_fr": smart_result.get('rewrite_fr', ''),
                    "rewrite_en": smart_result.get('rewrite_en', ''),
                    "full_smart_analysis": smart_result,
                    "full_alignment_analysis": alignment_result
                },
                "success": True
            })

        except Exception as e:
            results.append({
                "objective_id": obj["objective_id"],
                "title": obj["title"],
                "description": obj["description"],
                "origin": obj["origin"],
                "analysis": None,
                "error": str(e),
                "success": False
            })

    return results


def create_result_excel(
    original_wb,
    analysis_results: List[Dict[str, Any]],
    original_objective_col: int,
    original_description_col: Optional[int],
    sheet_name: Optional[str] = None
) -> io.BytesIO:
    """Crée un Excel reprenant la structure d'origine + colonnes d'analyse."""
    result_wb = Workbook()

    if sheet_name and sheet_name in original_wb.sheetnames:
        source_ws = original_wb[sheet_name]
    else:
        source_ws = original_wb.active

    result_ws = result_wb.active
    result_ws.title = source_ws.title

    for row_idx, row in enumerate(source_ws.iter_rows(values_only=True), 1):
        for col_idx, value in enumerate(row, 1):
            result_ws.cell(row=row_idx, column=col_idx, value=value)

    analysis_columns = [
        ("Score_SMART", "smart_score"),
        ("S", "s_score"),
        ("M", "m_score"),
        ("A", "a_score"),
        ("R", "r_score"),
        ("T", "t_score"),
        ("Score_Alignement", "alignment_score"),
        ("Alignement", "alignment_text"),
        ("Nb_Problèmes", "issues_count"),
        ("Problème_Principal", "top_issue"),
        ("Recommandations", "recommendations"),
        ("Gaps_Risques", "risks_or_gaps"),
        ("Reformulation_FR", "rewrite_fr"),
        ("Reformulation_EN", "rewrite_en")
    ]

    start_col = source_ws.max_column + 1

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col_offset, (header_name, _) in enumerate(analysis_columns):
        cell = result_ws.cell(row=1, column=start_col + col_offset, value=header_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    results_by_row = {r["origin"]["row_index"]: r for r in analysis_results if r.get("origin")}

    good_fill = PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid")
    medium_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
    bad_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")

    for row_idx in range(2, source_ws.max_row + 1):
        result = results_by_row.get(row_idx)

        if result and result.get("success") and result.get("analysis"):
            analysis = result["analysis"]

            for col_offset, (_, field_name) in enumerate(analysis_columns):
                cell = result_ws.cell(row=row_idx, column=start_col + col_offset)

                value = analysis.get(field_name, "")

                if isinstance(value, list):
                    value = "\n".join(str(v) for v in value[:3]) if value else ""

                cell.value = value
                cell.alignment = Alignment(wrap_text=True, vertical="top")

                if field_name == "smart_score":
                    if value >= 80:
                        cell.fill = good_fill
                    elif value >= 60:
                        cell.fill = medium_fill
                    else:
                        cell.fill = bad_fill
                elif field_name in ["s_score", "m_score", "a_score", "r_score", "t_score"]:
                    cell.fill = good_fill if value == 1 else bad_fill

    for col_offset, (header_name, _) in enumerate(analysis_columns):
        col_letter = openpyxl.utils.get_column_letter(start_col + col_offset)
        if "Reformulation" in header_name or "Recommandations" in header_name:
            result_ws.column_dimensions[col_letter].width = 50
        elif "Problème" in header_name:
            result_ws.column_dimensions[col_letter].width = 40
        else:
            result_ws.column_dimensions[col_letter].width = 15

    output = io.BytesIO()
    result_wb.save(output)
    output.seek(0)

    return output


# ============================================================================
# ORCHESTRATION (appelée par ai_controller) — lecture fichier + analyse + stockage
# ============================================================================

_ALLOWED_IMPORT_ROLES = ("COLLAB", "MANAGER", "HR")


def _load_workbook_or_400(content: bytes, filename: str):
    """Charge le classeur en validant le support et l'extension (sinon 4xx/5xx)."""
    if not EXCEL_SUPPORT:
        raise HTTPException(status_code=500, detail="Support Excel non disponible. Installez openpyxl.")
    if not filename or not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Format de fichier non supporté. Utilisez .xlsx ou .xls")
    return openpyxl.load_workbook(io.BytesIO(content), data_only=True)


def _store_result_by_role(db, role: str, user_id: str, result: dict) -> None:
    """Stocke un résultat d'analyse dans la table privée correspondant au rôle."""
    result_id = f"import-{secrets.token_hex(6)}"
    analysis = result["analysis"]
    now = datetime.now().isoformat()
    common = {
        "smart_score": analysis["smart_score"],
        "alignment_score": analysis["alignment_score"],
        "s_score": analysis["s_score"], "m_score": analysis["m_score"],
        "a_score": analysis["a_score"], "r_score": analysis["r_score"],
        "t_score": analysis["t_score"],
        "issues_count": analysis["issues_count"], "top_issue": analysis["top_issue"],
        "objective_title": result["title"],
        "smart_analysis": json.dumps(analysis["full_smart_analysis"]),
        "alignment_analysis": json.dumps(analysis["full_alignment_analysis"]),
        "analyzed_at": now,
    }
    if role == "MANAGER":
        analysis_repository.insert_manager(db, {
            "id": result_id, "objective_id": f"imported-{result_id}",
            "manager_id": user_id, **common,
        })
    elif role == "HR":
        analysis_repository.insert_hr(db, {
            "id": result_id, "objective_id": f"hr-obj-{result_id}", **common,
        })
    elif role == "COLLAB":
        analysis_repository.insert_collab(db, {
            "id": result_id, "objective_id": f"imported-{result_id}",
            "user_id": user_id,
            "objective_description": result.get("description", ""),
            "rewrite_fr": analysis.get("rewrite_fr", ""),
            "rewrite_en": analysis.get("rewrite_en", ""),
            **common,
        })


def run_scan(content: bytes, filename: str) -> dict:
    """Scanne la structure d'un fichier Excel (prévisualisation avant import)."""
    wb = _load_workbook_or_400(content, filename)
    try:
        return {"success": True, "filename": filename, "scan": scan_excel_file(wb)}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Excel Scan Error] {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse du fichier Excel.")


def run_import_analyze(content: bytes, filename: str, current_user: dict) -> dict:
    """Import + analyse en lot ; stocke les résultats dans la table privée du rôle."""
    if current_user["role"] not in _ALLOWED_IMPORT_ROLES:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")
    wb = _load_workbook_or_400(content, filename)

    try:
        scan_result = scan_excel_file(wb)
        if not scan_result["best_objective_column"]:
            raise HTTPException(
                status_code=400,
                detail="Impossible de détecter une colonne d'objectifs. Assurez-vous que le fichier contient une colonne avec des titres d'objectifs.",
            )

        objective_col = scan_result["best_objective_column"]["index"]
        description_col = scan_result["best_description_column"]["index"] if scan_result["best_description_column"] else None
        sheet_name = scan_result["best_objective_column"]["sheet"]

        objectives = extract_objectives_from_excel(wb, objective_col, description_col, sheet_name)
        if not objectives:
            raise HTTPException(status_code=400, detail="Aucun objectif valide trouvé dans le fichier.")

        with db_session() as db:
            company_objectives = company_objective_repository.list_for_alignment(db)

        analysis_results = analyze_objectives_batch(objectives, company_objectives)
        successful_results = [r for r in analysis_results if r.get("success")]

        with db_session() as db:
            for result in successful_results:
                _store_result_by_role(db, current_user["role"], current_user["id"], result)

        return {
            "success": True,
            "scan_info": {
                "total_sheets": scan_result["total_sheets"],
                "selected_sheet": sheet_name,
                "detected_objective_column": scan_result["best_objective_column"],
                "detected_description_column": scan_result["best_description_column"],
            },
            "extraction_info": {
                "total_extracted": len(objectives),
                "total_analyzed": len(successful_results),
                "total_errors": len(analysis_results) - len(successful_results),
            },
            "results": [
                {
                    "objective_id": r["objective_id"],
                    "title": r["title"],
                    "description": r["description"],
                    "smart_score": r["analysis"]["smart_score"] if r.get("analysis") else None,
                    "alignment_score": r["analysis"]["alignment_score"] if r.get("analysis") else None,
                    "alignment_text": r["analysis"]["alignment_text"] if r.get("analysis") else None,
                    "s_score": r["analysis"]["s_score"] if r.get("analysis") else 0,
                    "m_score": r["analysis"]["m_score"] if r.get("analysis") else 0,
                    "a_score": r["analysis"]["a_score"] if r.get("analysis") else 0,
                    "r_score": r["analysis"]["r_score"] if r.get("analysis") else 0,
                    "t_score": r["analysis"]["t_score"] if r.get("analysis") else 0,
                    "recommendations": r["analysis"]["recommendations"] if r.get("analysis") else [],
                    "rewrite_fr": r["analysis"]["rewrite_fr"] if r.get("analysis") else "",
                    "rewrite_en": r["analysis"]["rewrite_en"] if r.get("analysis") else "",
                    "smart_analysis": r["analysis"]["full_smart_analysis"] if r.get("analysis") else None,
                    "alignment_analysis": r["analysis"]["full_alignment_analysis"] if r.get("analysis") else None,
                    "success": r["success"],
                    "error": r.get("error"),
                }
                for r in analysis_results
            ],
            "message": f"{len(successful_results)} objectif(s) analysé(s) avec succès sur {len(objectives)} extraits.",
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Excel Import Error] {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de l'import du fichier Excel.")


def run_import_export(content: bytes, filename: str, current_user: dict) -> io.BytesIO:
    """Import + analyse ; retourne un classeur Excel enrichi (structure conservée)."""
    if current_user["role"] not in _ALLOWED_IMPORT_ROLES:
        raise HTTPException(status_code=403, detail="Accès non autorisé.")
    wb = _load_workbook_or_400(content, filename)

    try:
        scan_result = scan_excel_file(wb)
        if not scan_result["best_objective_column"]:
            raise HTTPException(status_code=400, detail="Impossible de détecter une colonne d'objectifs.")

        objective_col = scan_result["best_objective_column"]["index"]
        description_col = scan_result["best_description_column"]["index"] if scan_result["best_description_column"] else None
        sheet_name = scan_result["best_objective_column"]["sheet"]

        objectives = extract_objectives_from_excel(wb, objective_col, description_col, sheet_name)
        if not objectives:
            raise HTTPException(status_code=400, detail="Aucun objectif valide trouvé.")

        with db_session() as db:
            company_objectives = company_objective_repository.list_for_alignment(db)

        analysis_results = analyze_objectives_batch(objectives, company_objectives)
        return create_result_excel(wb, analysis_results, objective_col, description_col, sheet_name)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Excel Export Error] {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la génération du fichier Excel.")
