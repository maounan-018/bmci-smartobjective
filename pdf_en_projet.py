#!/usr/bin/env python3
"""
pdf_en_projet.py — Reconstruit le code a partir des PDF (aller-retour inverse).

OBJECTIF
    Lit un dossier de PDF produits par projet_en_pdf.py et recree l'arborescence
    de code D'ORIGINE, octet pour octet. La fidelite vient de la PIECE JOINTE
    embarquee dans chaque PDF (les octets exacts du fichier), pas du texte
    affiche : on ne « relit » donc jamais du texte deforme.

    Le nom/extension d'origine est restaure depuis le MANIFESTE (_MANIFESTE_PDF.txt)
    genere a l'aller ; a defaut, depuis la metadonnee du PDF. Les octets viennent
    de la piece jointe, et le sha256 est verifie.

DEPENDANCES
    pip install pypdf

USAGE
    python pdf_en_projet.py                       # _pdf_export/ -> _code_reconstruit/
    python pdf_en_projet.py _pdf_export.zip        # depuis un ZIP directement
    python pdf_en_projet.py <src_pdf|zip> <dest>   # source + destination

    Sur VS Code : depose l'archive .zip, ouvre un terminal, puis lance
    `python pdf_en_projet.py mon_archive.zip` : tout le code reapparait dans
    _code_reconstruit/ (l'archive n'a meme pas besoin d'etre dezippee).
"""

import hashlib
import io
import os
import sys
import zipfile

try:
    from pypdf import PdfReader
except ImportError as e:
    print(f"[ERREUR] Dependance manquante : {e.name}")
    print("         pip install pypdf")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, "_pdf_export")
DEST = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(HERE, "_code_reconstruit")

META_PATH_KEY = "/OsaRelPath"
META_SHA_KEY = "/OsaSha256"
MANIFEST_NAME = "_MANIFESTE_PDF.txt"


def load_manifest(src: str) -> dict:
    """Lit le manifeste (pdf_relpath -> fichier d'origine), depuis un dossier OU un .zip."""
    raw = None
    try:
        if os.path.isfile(src) and src.lower().endswith(".zip"):
            with zipfile.ZipFile(src) as zf:
                for info in zf.infolist():
                    if os.path.basename(info.filename) == MANIFEST_NAME:
                        raw = zf.read(info).decode("utf-8", "replace")
                        break
        elif os.path.isdir(src):
            p = os.path.join(src, MANIFEST_NAME)
            if os.path.isfile(p):
                with open(p, encoding="utf-8") as f:
                    raw = f.read()
    except Exception:
        raw = None

    mapping = {}
    for line in (raw or "").splitlines():
        if not line or line.startswith("#") or "\t" not in line:
            continue
        pdf_rel, orig_rel = line.split("\t", 1)
        mapping[pdf_rel.strip().replace("\\", "/").lower()] = orig_rel.strip()
    return mapping


def extract_attachment(reader: PdfReader):
    """Retourne les octets de la 1re piece jointe du PDF, ou None."""
    try:
        attachments = reader.attachments  # Dict[str, List[bytes]]
    except Exception:
        attachments = {}
    for _name, payloads in (attachments or {}).items():
        if payloads:
            return payloads[0]
    return None


def safe_relpath(rel: str) -> str:
    """Nettoie un chemin relatif (anti remontee de dossier ../)."""
    rel = (rel or "").replace("\\", "/").lstrip("/")
    parts = [p for p in rel.split("/") if p not in ("", ".", "..")]
    return os.path.join(*parts) if parts else ""


def iter_pdfs(src: str):
    """Produit (label, octets_pdf) depuis un dossier OU une archive .zip."""
    if os.path.isfile(src) and src.lower().endswith(".zip"):
        with zipfile.ZipFile(src) as zf:
            for info in zf.infolist():
                if info.filename.lower().endswith(".pdf"):
                    yield info.filename, zf.read(info)
    elif os.path.isdir(src):
        for dirpath, _dirs, files in os.walk(src):
            for name in files:
                if name.lower().endswith(".pdf"):
                    full = os.path.join(dirpath, name)
                    with open(full, "rb") as f:
                        yield os.path.relpath(full, src), f.read()


def main():
    is_zip = os.path.isfile(SRC) and SRC.lower().endswith(".zip")
    if not is_zip and not os.path.isdir(SRC):
        print(f"[ERREUR] Source introuvable (dossier ou .zip) : {SRC}")
        return 1

    print("=" * 60)
    print("  PDF -> Projet (reconstruction du code)")
    print(f"  Source : {SRC}" + ("  [ZIP]" if is_zip else ""))
    print(f"  Sortie : {DEST}")
    print("=" * 60)

    manifest = load_manifest(SRC)
    if manifest:
        print(f"  Manifeste : {len(manifest)} correspondance(s) chargee(s)")

    done = failed = 0
    for label, pdf_bytes in iter_pdfs(SRC):
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            meta = reader.metadata or {}

            # Nom/extension d'origine : MANIFESTE d'abord, puis metadonnee du PDF,
            # en dernier recours le nom du PDF (extension .pdf retiree).
            key = label.replace("\\", "/").lower()
            rel = manifest.get(key) or meta.get(META_PATH_KEY)
            if not rel:
                rel = label[:-4] if label.lower().endswith(".pdf") else label
            rel = safe_relpath(rel)
            if not rel:
                raise ValueError("chemin relatif vide")

            data = extract_attachment(reader)
            if data is None:
                raise ValueError("aucune piece jointe (PDF non genere par projet_en_pdf.py ?)")

            # Verification d'integrite si le sha256 a ete stocke.
            expected = meta.get(META_SHA_KEY)
            if expected and hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("sha256 different -> fichier corrompu")

            dest = os.path.join(DEST, rel)
            os.makedirs(os.path.dirname(dest) or DEST, exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            done += 1
            print(f"  [OK ] {rel}")
        except Exception as e:
            failed += 1
            print(f"  [ERR] {label} -> {e}")

    print("=" * 60)
    print(f"  Termine : {done} fichiers reconstruits, {failed} en echec.")
    print(f"  -> Code complet dans : {DEST}")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
