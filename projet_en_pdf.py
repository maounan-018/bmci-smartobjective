#!/usr/bin/env python3
"""
projet_en_pdf.py — Convertit TOUT le projet en PDF (un PDF par fichier).

OBJECTIF
    Produire une copie du projet ou l'on ne voit QUE des fichiers .pdf, tout en
    gardant la possibilite de reconstruire le code a l'identique (cf.
    pdf_en_projet.py). Chaque PDF :
      - AFFICHE le contenu du fichier (lecture humaine, numeros de ligne) ;
      - EMBARQUE les octets ORIGINAUX du fichier en piece jointe PDF + le chemin
        relatif en metadonnee. C'est cette piece jointe qui garantit une
        reconstruction parfaite (au bit pres), l'extraction de texte d'un PDF
        etant elle-meme imprecise (indentation, caracteres speciaux).

    L'arborescence est reproduite dans le dossier de sortie. L'extension d'origine
    est REMPLACEE par .pdf (pas ajoutee) : backend/app/main.py -> backend/app/main.pdf
    (et non main.py.pdf). Pour que l'operation inverse reste possible, un fichier
    _MANIFESTE_PDF.txt note la correspondance « pdf -> fichier d'origine ».

DEPENDANCES
    pip install reportlab pypdf      (deja dans requirements.txt du projet)

USAGE
    python projet_en_pdf.py                 # projet courant -> _pdf_export/
    python projet_en_pdf.py <src> <dest>    # dossiers personnalises
"""

import hashlib
import io
import os
import sys
import zipfile

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader, PdfWriter
except ImportError as e:
    print(f"[ERREUR] Dependance manquante : {e.name}")
    print("         pip install reportlab pypdf")
    sys.exit(1)

# --- Reglages -----------------------------------------------------------------
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(ROOT, "_pdf_export")

# Dossiers a NE JAMAIS convertir (bruit / volumineux / generes).
EXCLUDE_DIRS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache",
    "dist", "build", ".venv", "venv", "env", ".idea", "_pdf_export",
    "_code_reconstruit", ".vite", "coverage", ".cache",
}
# Fichiers ignores (eux-memes + artefacts).
EXCLUDE_FILES = {os.path.basename(__file__), "pdf_en_projet.py"}
EXCLUDE_EXT = {".pyc", ".pyo", ".lock"}
MAX_BYTES = 5 * 1024 * 1024  # on saute les fichiers > 5 Mo (rare en code source)

# Cle de metadonnee portant le chemin relatif (relue par pdf_en_projet.py).
META_PATH_KEY = "/OsaRelPath"
META_SHA_KEY = "/OsaSha256"
ATTACH_NAME = "source.bin"  # nom de la piece jointe (octets originaux)
MANIFEST_NAME = "_MANIFESTE_PDF.txt"  # correspondance pdf -> fichier d'origine (reversible)


def is_binary(data: bytes) -> bool:
    """Heuristique simple : presence d'octet nul => binaire."""
    return b"\x00" in data[:4096]


def _wrap(line: str, width: int):
    """Decoupe une ligne trop longue (affichage uniquement)."""
    line = line.replace("\t", "    ")
    if not line:
        return [""]
    return [line[i:i + width] for i in range(0, len(line), width)]


def render_visible_pdf(rel: str, data: bytes, binary: bool) -> bytes:
    """Construit le PDF lisible (contenu affiche). Retourne les octets PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin, size = 40, 8.5
    lh = size * 1.3
    max_chars = int((width - 2 * margin) / (size * 0.6))

    y = height - margin
    c.setFont("Courier-Bold", 10)
    c.drawString(margin, y, rel[:max_chars])
    y -= lh * 1.8
    c.setFont("Courier", size)

    if binary:
        c.drawString(margin, y, f"[fichier binaire : {len(data)} octets — contenu en piece jointe]")
    else:
        text = data.decode("utf-8", errors="replace")
        for n, raw in enumerate(text.split("\n"), start=1):
            for i, seg in enumerate(_wrap(raw, max_chars - 6)):
                if y < margin:
                    c.showPage()
                    c.setFont("Courier", size)
                    y = height - margin
                prefix = f"{n:>4}  " if i == 0 else "      "
                c.drawString(margin, y, prefix + seg)
                y -= lh
    c.showPage()
    c.save()
    return buf.getvalue()


def make_pdf(rel: str, data: bytes) -> bytes:
    """PDF lisible + piece jointe (octets exacts) + metadonnees (chemin, sha256)."""
    visible = render_visible_pdf(rel, data, is_binary(data))

    writer = PdfWriter(clone_from=io.BytesIO(visible))
    writer.add_attachment(ATTACH_NAME, data)
    writer.add_metadata({
        META_PATH_KEY: rel.replace("\\", "/"),
        META_SHA_KEY: hashlib.sha256(data).hexdigest(),
        "/Title": rel,
        "/Producer": "projet_en_pdf.py (ObjectifSMART-AI)",
    })
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def iter_files(root: str):
    """Parcourt le projet en ignorant les dossiers/fichiers exclus."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            if name in EXCLUDE_FILES or os.path.splitext(name)[1].lower() in EXCLUDE_EXT:
                continue
            yield os.path.join(dirpath, name)


def pdf_output_relpath(rel: str, used: set) -> str:
    """Chemin du PDF de sortie : extension d'origine REMPLACEE par .pdf (pas ajoutee).

    Ex : backend/app/main.py -> backend/app/main.pdf
    En cas de collision dans un meme dossier (app.py + app.js -> app.pdf), on
    suffixe (_2, _3...). La correspondance exacte est de toute facon consignee
    dans le manifeste, donc l'operation inverse reste fidele.
    """
    base, _ext = os.path.splitext(rel)
    candidate = base + ".pdf"
    n = 2
    while candidate.replace("\\", "/").lower() in used:
        candidate = f"{base}_{n}.pdf"
        n += 1
    used.add(candidate.replace("\\", "/").lower())
    return candidate


def main():
    if not os.path.isdir(ROOT):
        print(f"[ERREUR] Dossier source introuvable : {ROOT}")
        return 1

    print("=" * 60)
    print("  Projet -> PDF")
    print(f"  Source : {ROOT}")
    print(f"  Sortie : {OUT}")
    print("=" * 60)

    done = skipped = 0
    used: set = set()          # noms de PDF deja utilises (anti-collision)
    manifest: list = []        # (pdf_relpath, fichier_origine_relpath)
    for path in iter_files(ROOT):
        rel = os.path.relpath(path, ROOT)
        try:
            size = os.path.getsize(path)
            if size > MAX_BYTES:
                print(f"  [SAUTE] {rel} ({size} octets > {MAX_BYTES})")
                skipped += 1
                continue
            with open(path, "rb") as f:
                data = f.read()
            pdf_bytes = make_pdf(rel, data)
            pdf_rel = pdf_output_relpath(rel, used)   # extension REMPLACEE par .pdf
            dest = os.path.join(OUT, pdf_rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(pdf_bytes)
            manifest.append((pdf_rel.replace("\\", "/"), rel.replace("\\", "/")))
            done += 1
            print(f"  [PDF ] {rel}  ->  {pdf_rel}")
        except Exception as e:
            skipped += 1
            print(f"  [ERR ] {rel} -> {e}")

    # --- Manifeste : correspondance PDF -> fichier d'origine (operation inverse) ---
    manifest_path = os.path.join(OUT, MANIFEST_NAME)
    with open(manifest_path, "w", encoding="utf-8") as mf:
        mf.write("# Manifeste genere par projet_en_pdf.py — NE PAS SUPPRIMER / MODIFIER.\n")
        mf.write("# Relu par pdf_en_projet.py pour restaurer les noms et extensions d'origine.\n")
        mf.write("# Format (tabulation) : <pdf_relpath>\\t<fichier_origine_relpath>\n")
        for pdf_rel, orig_rel in manifest:
            mf.write(f"{pdf_rel}\t{orig_rel}\n")

    # --- Archive ZIP (PDF + manifeste, arborescence preservee a l'identique) ---
    zip_path = OUT + ".zip"
    zipped = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _dirs, files in os.walk(OUT):
            for name in files:
                if not (name.lower().endswith(".pdf") or name == MANIFEST_NAME):
                    continue
                full = os.path.join(dirpath, name)
                arcname = os.path.relpath(full, OUT).replace("\\", "/")
                zf.write(full, arcname)
                if name.lower().endswith(".pdf"):
                    zipped += 1

    print("=" * 60)
    print(f"  Termine : {done} PDF generes, {skipped} ignores.")
    print(f"  Dossier PDF : {OUT}")
    print(f"  Manifeste   : {manifest_path}")
    print(f"  Archive ZIP : {zip_path}  ({zipped} PDF + manifeste, arborescence intacte)")
    print("  -> Pour revenir au code (accepte le dossier OU le zip) :")
    print(f"     python pdf_en_projet.py \"{zip_path}\"")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
