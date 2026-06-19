#!/usr/bin/env python3
"""
pdf_en_projet.py — Reconstruit le code a partir des PDF (aller-retour inverse).

OBJECTIF
    Lit un dossier de PDF produits par projet_en_pdf.py et recree l'arborescence
    de code D'ORIGINE, octet pour octet. La fidelite vient de la PIECE JOINTE
    embarquee dans chaque PDF (les octets exacts du fichier), pas du texte
    affiche : on ne « relit » donc jamais du texte deforme.

    Pour chaque PDF : on lit le chemin relatif (metadonnee), on extrait la piece
    jointe (octets originaux), on verifie le sha256, puis on ecrit le fichier.

DEPENDANCES
    pip install pypdf

USAGE
    python pdf_en_projet.py                  # _pdf_export/ -> _code_reconstruit/
    python pdf_en_projet.py <src_pdf> <dest> # dossiers personnalises

    Sur VS Code : dezippe l'archive de PDF, ouvre un terminal dans le dossier,
    puis lance cette commande : tout le code reapparait dans _code_reconstruit/.
"""

import hashlib
import os
import sys

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


def main():
    if not os.path.isdir(SRC):
        print(f"[ERREUR] Dossier de PDF introuvable : {SRC}")
        return 1

    print("=" * 60)
    print("  PDF -> Projet (reconstruction du code)")
    print(f"  Source : {SRC}")
    print(f"  Sortie : {DEST}")
    print("=" * 60)

    done = failed = 0
    for dirpath, _dirs, files in os.walk(SRC):
        for name in files:
            if not name.lower().endswith(".pdf"):
                continue
            pdf_path = os.path.join(dirpath, name)
            try:
                reader = PdfReader(pdf_path)
                meta = reader.metadata or {}

                # Chemin relatif : metadonnee si presente, sinon deduit du nom du PDF.
                rel = meta.get(META_PATH_KEY)
                if not rel:
                    rel = os.path.relpath(pdf_path, SRC)
                    if rel.lower().endswith(".pdf"):
                        rel = rel[:-4]
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
                print(f"  [ERR] {name} -> {e}")

    print("=" * 60)
    print(f"  Termine : {done} fichiers reconstruits, {failed} en echec.")
    print(f"  -> Code complet dans : {DEST}")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
