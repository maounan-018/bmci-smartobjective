#!/usr/bin/env python3
"""
services/document_extractor.py — Extraction de texte des fichiers téléversés.

RÔLE
    Convertit le contenu binaire d'un fichier (PDF, Word, Excel, texte) en texte
    brut, prêt à être découpé puis indexé par `rag_service`. Le type est déduit de
    l'extension du nom de fichier. Les bibliothèques lourdes sont importées à la
    demande (lazy) pour ne charger que ce qui est nécessaire.

EMPLACEMENT MVC
    Couche "services" : utilitaire métier, sans route HTTP.
"""

import io
import logging

logger = logging.getLogger(__name__)

# Extensions supportées (déduites du nom de fichier).
SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".xlsx", ".txt", ".md")


def file_extension(filename: str) -> str:
    """Retourne l'extension en minuscules (point inclus), ou '' si absente."""
    name = (filename or "").lower().strip()
    dot = name.rfind(".")
    return name[dot:] if dot != -1 else ""


def extract_text(filename: str, content: bytes) -> str:
    """Extrait le texte d'un fichier selon son extension.

    Lève ValueError si le format n'est pas supporté ou si rien n'est extractible.
    """
    ext = file_extension(filename)
    if ext == ".pdf":
        text = _extract_pdf(content)
    elif ext == ".docx":
        text = _extract_docx(content)
    elif ext == ".xlsx":
        text = _extract_xlsx(content)
    elif ext in (".txt", ".md"):
        text = _extract_plain(content)
    else:
        raise ValueError(
            f"Format non supporté : '{ext or '?'}'. "
            f"Formats acceptés : {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    text = (text or "").strip()
    if not text:
        raise ValueError("Aucun texte extractible de ce fichier.")
    return text


def _extract_plain(content: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(parts)


def _extract_docx(content: bytes) -> str:
    import docx
    document = docx.Document(io.BytesIO(content))
    parts = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    # Tables Word : on aplatit chaque ligne (cellules séparées par « | »).
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n\n".join(parts)


def _extract_xlsx(content: bytes) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"# Feuille : {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                parts.append(" | ".join(cells))
    wb.close()
    return "\n".join(parts)
