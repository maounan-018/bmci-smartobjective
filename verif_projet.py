#!/usr/bin/env python3
"""
verif_projet.py - Diagnostic « pret a demarrer » sur un nouveau PC.

ROLE
    Verifie en une commande tout ce qui doit etre present pour que
    ObjectifSMART-AI tourne : version de Python, dependances backend, support
    sqlite-vec (RAG), dependances frontend, Ollama + ses modeles, fichiers
    critiques et disponibilite des ports. Affiche un go / no-go clair avec, pour
    chaque echec, la commande exacte qui repare.

    100% bibliotheque standard : se lance AVANT meme `pip install` (il dira juste
    quelles dependances manquent). Aucun effet de bord : ne modifie rien.

USAGE
    python verif_projet.py

CODE DE SORTIE
    0 = tout est pret (ou seulement des avertissements non bloquants)
    1 = au moins un point BLOQUANT (l'app ne demarrera pas correctement)
"""

import os
import sys
import json
import socket
import urllib.request

# Sortie UTF-8 tolerante (consoles Windows en cp1252 ne plantent pas).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.abspath(__file__))

# Marqueurs ASCII (compatibles cmd.exe sans page de code particuliere).
OK, FAIL, WARN, INFO = "[ OK ]", "[FAIL]", "[WARN]", "[ .. ]"

_problems = 0   # echecs bloquants
_warnings = 0   # avertissements non bloquants


def line(mark, label, detail=""):
    print(f"  {mark}  {label}" + (f"  ->  {detail}" if detail else ""))


def ok(label, detail=""):
    line(OK, label, detail)


def fail(label, fix):
    global _problems
    _problems += 1
    line(FAIL, label)
    print(f"           reparer : {fix}")


def warn(label, fix):
    global _warnings
    _warnings += 1
    line(WARN, label)
    print(f"           note    : {fix}")


def section(title):
    print(f"\n{title}")


# --------------------------------------------------------------------------- #
# 1. Python
# --------------------------------------------------------------------------- #
def check_python():
    section("1) Python")
    v = sys.version_info
    if (v.major, v.minor) >= (3, 10):
        ok(f"Version Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(
            f"Python {v.major}.{v.minor} trop ancien (>= 3.10 requis)",
            "installer Python 3.10+ depuis https://www.python.org/downloads/ "
            "(cocher 'Add Python to PATH')",
        )


# --------------------------------------------------------------------------- #
# 2. Dependances backend
# --------------------------------------------------------------------------- #
def check_backend_deps():
    section("2) Dependances backend (requirements.txt)")
    # nom d'import -> nom pip (pour le message de reparation)
    modules = {
        "fastapi": "fastapi", "uvicorn": "uvicorn", "requests": "requests",
        "pydantic": "pydantic", "sqlalchemy": "SQLAlchemy", "openpyxl": "openpyxl",
        "reportlab": "reportlab", "multipart": "python-multipart",
        "sqlite_vec": "sqlite-vec", "pypdf": "pypdf", "docx": "python-docx",
    }
    missing = []
    for imp, pip_name in modules.items():
        try:
            __import__(imp)
        except Exception:
            missing.append(pip_name)
    if not missing:
        ok("Toutes les dependances Python sont installees")
    else:
        fail(
            f"Dependances manquantes : {', '.join(missing)}",
            "pip install -r requirements.txt",
        )


# --------------------------------------------------------------------------- #
# 3. sqlite-vec (RAG / recherche semantique)
# --------------------------------------------------------------------------- #
def check_sqlite_vec():
    section("3) Recherche vectorielle RAG (sqlite-vec)")
    import sqlite3
    db = None
    try:
        db = sqlite3.connect(":memory:")
    except Exception as e:
        fail(f"SQLite indisponible : {e}", "reinstaller Python depuis python.org")
        return
    if not hasattr(db, "enable_load_extension"):
        warn(
            "Ce Python ne supporte pas le chargement d'extensions SQLite",
            "le RAG/Coach sera indisponible (le reste de l'app fonctionne). "
            "Utiliser le Python officiel python.org (PAS celui du Microsoft Store)",
        )
        return
    try:
        db.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(db)
        ver = db.execute("select vec_version()").fetchone()[0]
        ok(f"sqlite-vec operationnel (version {ver})")
    except Exception as e:
        warn(
            f"sqlite-vec ne se charge pas : {e}",
            "le RAG/Coach sera indisponible ; verifier 'pip install sqlite-vec'",
        )
    finally:
        try:
            db.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 4. Frontend (node_modules)
# --------------------------------------------------------------------------- #
def check_frontend():
    section("4) Frontend (dependances npm)")
    nm = os.path.join(ROOT, "frontend", "node_modules")
    if os.path.isdir(nm) and os.listdir(nm):
        ok("frontend/node_modules present")
    else:
        fail(
            "frontend/node_modules absent",
            "cd frontend && npm install  (necessite Node.js 18+ : https://nodejs.org)",
        )


# --------------------------------------------------------------------------- #
# 5. Ollama + modeles
# --------------------------------------------------------------------------- #
def check_ollama():
    section("5) IA locale (Ollama + modeles)")
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        names = [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        warn(
            "Ollama injoignable sur :11434",
            "le demarrer (`ollama serve`) ou l'installer : https://ollama.com/download. "
            "L'app demarre sans lui, mais les analyses IA ne marcheront pas",
        )
        return
    ok("Ollama repond sur :11434")

    # base -> commande de reparation
    needed = {
        "smart-qwen8": "ollama create smart-qwen8 -f Modelfile",
        "qwen3:8b": "ollama pull qwen3:8b",
        "bge-m3": "ollama pull bge-m3",
    }
    for model, fix in needed.items():
        present = any(n == model or n.startswith(model + ":") for n in names)
        if present:
            ok(f"Modele '{model}' present")
        else:
            warn(f"Modele '{model}' absent", fix)


# --------------------------------------------------------------------------- #
# 6. Fichiers critiques
# --------------------------------------------------------------------------- #
def check_files():
    section("6) Fichiers critiques")
    required = [
        "backend/.env", "backend/app/main.py", "requirements.txt",
        "Modelfile", "frontend/package.json", "frontend/vite.config.js",
    ]
    all_ok = True
    for rel in required:
        path = os.path.join(ROOT, *rel.split("/"))
        if not os.path.exists(path):
            all_ok = False
            fail(f"Fichier manquant : {rel}", "re-cloner le depot (copie incomplete)")
        elif os.path.getsize(path) == 0:
            all_ok = False
            fail(f"Fichier vide (copie corrompue) : {rel}", "re-cloner le depot")
    if all_ok:
        ok("Tous les fichiers critiques sont presents et non vides")


# --------------------------------------------------------------------------- #
# 7. Ports
# --------------------------------------------------------------------------- #
def _port_busy(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def check_ports():
    section("7) Ports (5001 backend / 3000 frontend)")
    for port, role in ((5001, "backend"), (3000, "frontend")):
        if _port_busy(port):
            warn(
                f"Port {port} ({role}) deja occupe",
                "soit l'app tourne deja, soit un autre programme l'utilise",
            )
        else:
            ok(f"Port {port} ({role}) libre")


# --------------------------------------------------------------------------- #
def main():
    print("=" * 60)
    print("  ObjectifSMART-AI - Diagnostic 'pret a demarrer'")
    print("=" * 60)

    check_python()
    check_backend_deps()
    check_sqlite_vec()
    check_frontend()
    check_ollama()
    check_files()
    check_ports()

    print("\n" + "=" * 60)
    if _problems:
        print(f"  RESULTAT : {_problems} point(s) BLOQUANT(s), "
              f"{_warnings} avertissement(s).")
        print("  -> Corriger les [FAIL] ci-dessus avant de lancer LANCER_APP.bat")
        print("=" * 60)
        return 1
    if _warnings:
        print(f"  RESULTAT : pret a demarrer, avec {_warnings} avertissement(s).")
        print("  -> Les [WARN] n'empechent pas le demarrage (souvent : Ollama/modeles).")
        print("=" * 60)
        return 0
    print("  RESULTAT : tout est pret. Lance LANCER_APP.bat (ou ./start_app.sh).")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
