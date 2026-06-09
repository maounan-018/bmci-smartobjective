#!/usr/bin/env python3
"""
verif_projet.py — Diagnostic complet du projet ObjectifSMART-AI BMCI
Lance : python verif_projet.py
"""

import os
import sys

# ── Détection automatique de la racine du projet ──────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))

ok_count = 0
warn_count = 0
err_count = 0

def c(color, text):
    colors = {"green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m",
              "cyan": "\033[96m", "white": "\033[97m", "reset": "\033[0m", "bold": "\033[1m"}
    return f"{colors.get(color,'')}{text}{colors['reset']}"

def check_file(rel_path, must_contain=None, min_lines=3):
    global ok_count, warn_count, err_count
    full = os.path.join(ROOT, rel_path)
    if not os.path.exists(full):
        print(c("red", f"  [MANQUANT]  {rel_path}"))
        err_count += 1
        return
    try:
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        print(c("red", f"  [ERREUR LECTURE] {rel_path} — {e}"))
        err_count += 1
        return
    count = len(lines)
    if count < min_lines:
        print(c("yellow", f"  [TRONQUE {count} lignes]  {rel_path}"))
        warn_count += 1
        return
    if must_contain:
        content = "".join(lines)
        found = any(kw in content for kw in must_contain)
        if not found:
            print(c("yellow", f"  [INCOMPLET {count} lignes]  {rel_path}  (cherche: {must_contain[0]})"))
            warn_count += 1
            return
    print(c("green", f"  [OK {count} lignes]  {rel_path}"))
    ok_count += 1

def check_dir(rel_path):
    global ok_count, err_count
    full = os.path.join(ROOT, rel_path)
    if os.path.isdir(full):
        print(c("green", f"  [OK]  {rel_path}/"))
        ok_count += 1
    else:
        print(c("red", f"  [MANQUANT]  {rel_path}/"))
        err_count += 1

def section(title):
    print(c("cyan", f"\n{'─'*50}"))
    print(c("bold", f"  {title}"))
    print(c("cyan", f"{'─'*50}"))

# ══════════════════════════════════════════════════════════════════════════════
print(c("cyan", "\n" + "═"*55))
print(c("bold",   "   DIAGNOSTIC COMPLET — ObjectifSMART-AI BMCI"))
print(c("cyan",   f"   Racine détectée : {ROOT}"))
print(c("cyan",   "═"*55))

# ── 1. DOSSIERS ───────────────────────────────────────────────────────────────
section("1. DOSSIERS OBLIGATOIRES")
dirs = [
    "backend/app",
    "backend/app/controllers",
    "backend/app/services",
    "backend/app/models",
    "backend/app/schemas",
    "backend/app/core",
    "backend/app/database",
    "backend/app/middlewares",
    "backend/app/repositories",
    "backend/app/auth",
    "backend/app/utils",
    "frontend/src",
    "frontend/src/views",
    "frontend/src/stores",
    "frontend/src/services",
    "frontend/src/router",
    "frontend/src/components",
]
for d in dirs:
    check_dir(d)

# ── 2. BACKEND PRINCIPAL ──────────────────────────────────────────────────────
section("2. BACKEND — Fichiers principaux")
check_file("backend/app/main.py",            ["create_app", "app = create_app"], 20)
check_file("backend/app/core/config.py",     ["ALLOWED_ORIGINS", "Settings"],    30)
check_file("backend/app/core/security.py",   ["hash_password", "verify_password"], 10)
check_file("backend/app/database/init_db.py",["init_db", "Base.metadata"],       10)
check_file("requirements.txt",               ["fastapi", "uvicorn"],               5)

# ── 3. CONTROLEURS ────────────────────────────────────────────────────────────
section("3. BACKEND — Contrôleurs")
for ctrl in ["auth_controller", "hr_controller", "manager_controller",
             "objective_controller", "ai_controller", "admin_controller"]:
    check_file(f"backend/app/controllers/{ctrl}.py", ["router", "APIRouter"], 10)

# ── 4. SERVICES ───────────────────────────────────────────────────────────────
section("4. BACKEND — Services")
check_file("backend/app/services/auth_service.py",          ["def login", "def register"], 20)
check_file("backend/app/services/hr_service.py",            ["def "],  20)
check_file("backend/app/services/objective_service.py",     ["def "],  20)
check_file("backend/app/services/manager_service.py",       ["def "],  20)
check_file("backend/app/services/ai_service.py",            ["def "],  20)
check_file("backend/app/services/user_service.py",          ["def "],  10)
check_file("backend/app/services/audit_service.py",         ["def "],  10)
check_file("backend/app/services/export_service.py",        ["def "],  10)
check_file("backend/app/services/permission_service.py",    ["def "],  10)
check_file("backend/app/services/excel_import_service.py",  ["def "],  10)

# ── 5. MODELES ────────────────────────────────────────────────────────────────
section("5. BACKEND — Modèles SQLAlchemy")
for m in ["user", "objective", "session", "audit_log",
          "company_objective", "hr_import", "analysis_result"]:
    check_file(f"backend/app/models/{m}.py", ["class ", "Column"], 10)

# ── 6. SCHEMAS ────────────────────────────────────────────────────────────────
section("6. BACKEND — Schémas Pydantic")
for s in ["auth_schema", "hr_schema", "objective_schema", "user_schema", "analysis_schema"]:
    check_file(f"backend/app/schemas/{s}.py", ["class ", "BaseModel"], 10)

# ── 7. FICHIER .ENV ───────────────────────────────────────────────────────────
section("7. FICHIER .ENV (obligatoire)")
env_path = os.path.join(ROOT, "backend", ".env")
if not os.path.exists(env_path):
    print(c("red", "  [MANQUANT]  backend/.env  <- LE BACKEND NE PEUT PAS DEMARRER !"))
    err_count += 1
    print(c("yellow", "\n  Crée le fichier backend/.env avec ce contenu minimal :"))
    print(c("white", """
  APP_NAME=ObjectifSMART-AI
  OLLAMA_URL=http://localhost:11434/api/generate
  OLLAMA_MODEL=smart-qwen8
  DATABASE_PATH=objectifsmart.db
  SESSION_DURATION_HOURS=24
  PBKDF2_ITERATIONS=200000
  MAX_LOGIN_ATTEMPTS=5
  LOGIN_LOCKOUT_MINUTES=15
  MAX_REQUEST_SIZE_MB=20
  ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
"""))
else:
    content = open(env_path, encoding="utf-8", errors="ignore").read()
    missing_keys = []
    for k in ["ALLOWED_ORIGINS", "DATABASE_PATH", "OLLAMA_MODEL"]:
        if k not in content:
            missing_keys.append(k)
    if missing_keys:
        print(c("yellow", f"  [INCOMPLET]  backend/.env — clés manquantes : {', '.join(missing_keys)}"))
        warn_count += 1
    else:
        print(c("green", "  [OK]  backend/.env (toutes les clés présentes)"))
        ok_count += 1

# ── 8. FRONTEND ───────────────────────────────────────────────────────────────
section("8. FRONTEND — Fichiers Vue.js")
check_file("frontend/index.html",                          ["div", "app"],          5)
check_file("frontend/package.json",                        ["vue", "vite"],          5)
check_file("frontend/vite.config.js",                      ["defineConfig", "vue"],  5)
check_file("frontend/src/main.js",                         ["createApp", "App"],     5)
check_file("frontend/src/views/LoginView.vue",             ["login", "password"],   20)
check_file("frontend/src/views/HrDashboard.vue",           ["template", "script"],  50)
check_file("frontend/src/views/ManagerDashboard.vue",      ["template", "script"],  50)
check_file("frontend/src/views/CollaboratorDashboard.vue", ["template", "script"],  50)
check_file("frontend/src/stores/authStore.js",             ["defineStore"],         10)
check_file("frontend/src/services/api.js",                 ["fetch", "localhost"],  10)
check_file("frontend/src/router/index.js",                 ["createRouter"],        10)

# ── 9. NODE_MODULES ───────────────────────────────────────────────────────────
section("9. FRONTEND — node_modules (npm install)")
nm = os.path.join(ROOT, "frontend", "node_modules")
if os.path.isdir(nm):
    pkgs = [d for d in os.listdir(nm) if os.path.isdir(os.path.join(nm, d))]
    print(c("green", f"  [OK]  node_modules ({len(pkgs)} paquets installés)"))
    ok_count += 1
else:
    print(c("red", "  [MANQUANT]  frontend/node_modules"))
    print(c("yellow", "  -> Lance : cd frontend && npm install"))
    err_count += 1

# ── 10. FICHIERS RACINE ───────────────────────────────────────────────────────
section("10. FICHIERS RACINE")
check_file("Modelfile",        ["FROM qwen", "SYSTEM"], 5)
check_file("requirements.txt", ["fastapi", "uvicorn"],  5)
check_file("LANCER_APP.bat",   ["uvicorn", "npm"],      5)

# ── 11. VERIF PYTHON & NODE ───────────────────────────────────────────────────
section("11. ENVIRONNEMENT SYSTEME")
import subprocess

for cmd, label in [("python --version", "Python"), ("pip --version", "pip"),
                   ("node --version", "Node.js"), ("npm --version", "npm"),
                   ("ollama --version", "Ollama")]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        ver = (r.stdout or r.stderr).strip().split("\n")[0]
        if ver:
            print(c("green", f"  [OK]  {label} : {ver}"))
            ok_count += 1
        else:
            print(c("red", f"  [MANQUANT]  {label} — non trouvé dans PATH"))
            err_count += 1
    except Exception:
        print(c("red", f"  [MANQUANT]  {label} — non trouvé"))
        err_count += 1

# ── 12. TEST PORTS ────────────────────────────────────────────────────────────
section("12. TEST DES PORTS (services démarrés ?)")
import socket

for port, name in [(5001, "Backend FastAPI"), (3000, "Frontend Vue"), (11434, "Ollama")]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(("127.0.0.1", port))
    s.close()
    if result == 0:
        print(c("green", f"  [EN LIGNE]  port {port} — {name} OK"))
        ok_count += 1
    else:
        print(c("yellow", f"  [ETEINT]    port {port} — {name} (pas encore démarré)"))
        warn_count += 1

# ══ RÉSULTAT FINAL ════════════════════════════════════════════════════════════
print(c("cyan", "\n" + "═"*55))
print(c("bold", "   RESULTAT FINAL"))
print(c("cyan", "═"*55))
print(c("green",  f"  OK        : {ok_count}"))
print(c("yellow", f"  INCOMPLET : {warn_count}"))
print(c("red",    f"  MANQUANT  : {err_count}"))

total = ok_count + warn_count + err_count
if total > 0:
    pct = int(ok_count / total * 100)
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    print(c("white", f"\n  Completude : [{bar}] {pct}%\n"))

if err_count > 0:
    print(c("red",    "  FICHIERS MANQUANTS detectes !"))
    print(c("white",  "  -> Envoie une capture de ce resultat.\n"))
elif warn_count > 0:
    print(c("yellow", "  FICHIERS INCOMPLETS/TRONQUES detectes !"))
    print(c("white",  "  -> Envoie une capture pour corriger.\n"))
else:
    print(c("green",  "  PROJET COMPLET — Tous les fichiers sont presents !"))
    print(c("white",  "  -> Lance maintenant :"))
    print(c("white",  "     1. ollama serve"))
    print(c("white",  "     2. cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload"))
    print(c("white",  "     3. cd frontend && npm run dev"))
    print(c("white",  "     4. Ouvre http://localhost:3000\n"))
