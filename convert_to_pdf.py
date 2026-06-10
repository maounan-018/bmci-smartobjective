#!/usr/bin/env python3
"""
convert_to_pdf.py — Convertit tous les fichiers d'un dossier en PDF.
Conserve l'arborescence exacte. Seules les extensions changent en .pdf

Usage :
    python convert_to_pdf.py                        # convertit le dossier courant
    python convert_to_pdf.py C:\mon\projet          # convertit un dossier précis
    python convert_to_pdf.py C:\mon\projet  sortie  # dossier de sortie personnalisé
"""

import os
import sys

# ── Dépendance : reportlab (pip install reportlab) ────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_LEFT
except ImportError:
    print("[ERREUR] reportlab n'est pas installe.")
    print("         Lance : pip install reportlab")
    sys.exit(1)

# ── Dossiers/fichiers à ignorer ───────────────────────────────────────────────
SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".venv", "venv",
    ".pytest_cache", "dist", "build", ".next", ".nuxt",
    ".idea", ".vscode", "coverage", ".mypy_cache",
}
SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin",
    ".jpg", ".jpeg", ".png", ".gif", ".ico", ".svg", ".webp",
    ".mp4", ".mp3", ".zip", ".tar", ".gz", ".rar",
    ".db", ".sqlite", ".sqlite3",
    ".pdf",  # ne pas re-convertir des PDFs existants
}

# ── Couleurs & styles ─────────────────────────────────────────────────────────
HEADER_COLOR   = colors.HexColor("#1e3a5f")   # bleu marine BMCI
CODE_BG        = colors.HexColor("#f4f6f9")
LINE_COLOR     = colors.HexColor("#c8d4e3")
TEXT_COLOR     = colors.HexColor("#1a1a2e")
SUBTEXT_COLOR  = colors.HexColor("#6b7280")


def make_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FileTitle",
        parent=styles["Normal"],
        fontSize=13,
        textColor=HEADER_COLOR,
        fontName="Helvetica-Bold",
        spaceAfter=4,
        leading=16,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=8,
        textColor=SUBTEXT_COLOR,
        fontName="Helvetica",
        spaceAfter=8,
        leading=10,
    )
    code_style = ParagraphStyle(
        "Code",
        parent=styles["Normal"],
        fontSize=7.5,
        fontName="Courier",
        textColor=TEXT_COLOR,
        leftIndent=8,
        rightIndent=8,
        leading=11,
        backColor=CODE_BG,
        borderPad=6,
        spaceAfter=0,
        spaceBefore=0,
    )
    return title_style, meta_style, code_style


def escape_xml(text):
    """Échappe les caractères spéciaux pour ReportLab."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def read_file_safe(filepath):
    """Lit un fichier texte en gérant les encodages et les fichiers binaires."""
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(filepath, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    return None  # fichier binaire


def convert_file_to_pdf(src_path, dst_path, rel_path):
    """Convertit un fichier source en PDF à dst_path."""
    content = read_file_safe(src_path)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

    doc = SimpleDocTemplate(
        dst_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    title_style, meta_style, code_style = make_styles()
    story = []

    # ── En-tête du fichier ───────────────────────────────────────────────────
    filename  = os.path.basename(src_path)
    file_size = os.path.getsize(src_path)
    size_str  = f"{file_size:,} octets" if file_size < 1024 else f"{file_size/1024:.1f} Ko"

    story.append(Paragraph(escape_xml(filename), title_style))
    story.append(Paragraph(
        f"Chemin : {escape_xml(rel_path)}   •   Taille : {size_str}",
        meta_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=LINE_COLOR, spaceAfter=10))

    # ── Contenu ──────────────────────────────────────────────────────────────
    if content is None:
        story.append(Paragraph(
            "[Fichier binaire — contenu non affichable]",
            meta_style,
        ))
    else:
        lines = content.splitlines()
        if not lines:
            story.append(Paragraph("[Fichier vide]", meta_style))
        else:
            for line in lines:
                safe = escape_xml(line) if line.strip() else "&nbsp;"
                story.append(Paragraph(safe, code_style))

    doc.build(story)


def convert_tree(src_root, dst_root):
    """Parcourt src_root récursivement et convertit chaque fichier en PDF dans dst_root."""
    total = 0
    skipped = 0
    errors = 0

    for dirpath, dirnames, filenames in os.walk(src_root):
        # Filtrer les dossiers à ignorer (in-place pour éviter la descente)
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SKIP_EXTENSIONS:
                skipped += 1
                continue

            src_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(src_path, src_root)

            # Même chemin dans dst_root, extension → .pdf
            base_name  = os.path.splitext(filename)[0]
            dst_dir    = os.path.join(dst_root, os.path.dirname(rel_path))
            dst_path   = os.path.join(dst_dir, base_name + ".pdf")

            try:
                convert_file_to_pdf(src_path, dst_path, rel_path)
                print(f"  [OK]  {rel_path}  →  {os.path.relpath(dst_path, dst_root)}")
                total += 1
            except Exception as e:
                print(f"  [ERR] {rel_path}  →  {e}")
                errors += 1

    return total, skipped, errors


# ── Point d'entrée ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Source : argument 1 ou dossier courant
    src = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()

    # Destination : argument 2 ou <nom_source>_pdf à côté de la source
    if len(sys.argv) > 2:
        dst = os.path.abspath(sys.argv[2])
    else:
        parent = os.path.dirname(src)
        name   = os.path.basename(src)
        dst    = os.path.join(parent, name + "_pdf")

    print(f"\n{'='*55}")
    print(f"  CONVERSION PDF")
    print(f"  Source  : {src}")
    print(f"  Sortie  : {dst}")
    print(f"{'='*55}\n")

    if not os.path.isdir(src):
        print(f"[ERREUR] Dossier source introuvable : {src}")
        sys.exit(1)

    total, skipped, errors = convert_tree(src, dst)

    print(f"\n{'='*55}")
    print(f"  RESULTAT")
    print(f"  Convertis : {total}")
    print(f"  Ignores   : {skipped}  (binaires/images/.pyc...)")
    print(f"  Erreurs   : {errors}")
    print(f"  Dossier   : {dst}")
    print(f"{'='*55}\n")
