# 🎯 ObjectifSMART-AI — BMCI

Application d'analyse des objectifs **SMART** pour la BMCI, propulsée par une IA
locale (**Ollama**). L'application aide collaborateurs, managers et RH à évaluer
la qualité SMART des objectifs et leur alignement stratégique, le tout **sans
jamais envoyer de données hors de l'infrastructure de la banque**.

> Version 3.0 — Frontend migré vers **Vue.js (JavaScript)**, backend **Python
> FastAPI** restructuré en architecture **MVC**, sécurité et traçabilité
> renforcées. Le backend reste l'unique source de vérité pour la sécurité.

## 🏗️ Architecture

```
┌──────────────────────┐     ┌──────────────────────────┐     ┌─────────────────────┐
│   Frontend Vue.js     │────▶│   Backend FastAPI (MVC)   │────▶│   Ollama (local)    │
│   (Vite — :3000)      │     │   (Python — :5001)        │     │   smart-qwen8       │
└──────────────────────┘     └──────────────────────────┘     └─────────────────────┘
        proxy /api  ─────────────────▶  source de vérité sécurité
```

### Structure du backend (MVC) — `backend/app/`

```
backend/app/
├── main.py                 # Fabrique FastAPI + montage des routeurs + init_db (lifespan)
├── core/                   # config (.env) + security (PBKDF2, tokens, rate limiting)
├── database/               # SQLAlchemy : base (déclarative), session (engine + db_session), init_db
├── models/                 # modèles ORM (User, Session, Objective, CompanyObjective,
│                           #   AnalysisResult [hr/manager/collab], AuditLog, HRImport)
├── schemas/                # schémas Pydantic par domaine (auth, user, objective, analysis, hr)
├── controllers/            # routes FastAPI par domaine (fines — délèguent aux services)
│   ├── auth_controller.py      # /api/auth/* (+ dépendance get_current_user)
│   ├── admin_controller.py     # /api/admin/audit-logs
│   ├── objective_controller.py # /api/objectives, /api/company-objectives, /api/team
│   ├── manager_controller.py   # /api/manager/*, /api/collab/analysis-results
│   ├── hr_controller.py        # /api/hr/* (analytics, imports, exports)
│   └── ai_controller.py        # /api/analyze-*, /api/import-excel-*, /api/scan-excel, /api/managers
├── services/               # logique métier (auth, user, objective, manager, hr, ai,
│                           #   audit, export, excel_import, permission)
├── repositories/           # accès aux données (SQLAlchemy) — user, session, objective,
│                           #   company_objective, analysis, audit, hr_import
├── auth/                   # contrat d'identité + providers/ (local → LDAP/SSO demain)
├── middlewares/            # protections transverses (taille de requête)
├── utils/                  # helpers purs (calculs SMART, métadonnées requête)
└── tests/                  # tests sécurité/traçabilité/RBAC/import (pytest)
```

> **Couches** : `controllers` (routes) → `services` (logique métier) → `repositories`
> (requêtes SQLAlchemy) → `models` (ORM). Aucun SQL brut hors des repositories.

## 📋 Prérequis

1. **Node.js** v18+ (frontend Vue.js)
2. **Python** 3.10+ (backend FastAPI)
3. **Ollama** installé et configuré

## 🚀 Installation

### 1. Installer Ollama

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh
# Windows : télécharger depuis https://ollama.com
```

### 2. Créer le modèle SMART

```bash
ollama create smart-qwen8 -f Modelfile
```

### 3. Installer les dépendances

```bash
# Backend Python (depuis la racine du projet)
pip install -r requirements.txt

# Frontend Vue.js
cd frontend && npm install
```

### 4. Configurer l'environnement

```bash
# Copier le modèle puis renseigner les valeurs réelles
cp .env.example .env

# Générer une clé secrète robuste
python -c "import secrets; print(secrets.token_hex(32))"
# → coller le résultat dans SECRET_KEY du fichier .env
```

> ⚠️ **Sécurité** : ne jamais committer `.env` (déjà ignoré par git). Les mots
> de passe de seed (`SEED_*`) sont réservés au développement et doivent être
> changés hors de cet environnement.

## 🎮 Lancement

**Terminal 1 — Ollama :**
```bash
ollama serve
```

**Terminal 2 — Backend FastAPI (MVC) :**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

**Terminal 3 — Frontend Vue.js :**
```bash
cd frontend
npm run dev
```

## 🌐 Accès

- **Frontend :** http://localhost:3000
- **Backend API :** http://localhost:5001
- **Documentation interactive (Swagger) :** http://localhost:5001/docs
- **Health check :** http://localhost:5001/health

## 🔒 Sécurité & traçabilité

- **Mots de passe** : hachage **PBKDF2-HMAC-SHA256** salé (jamais de mot de passe
  stocké en clair ; migration transparente depuis l'ancien format SHA-256).
- **Sessions** : tokens aléatoires (`secrets`), expiration configurable.
- **Anti brute-force** : limitation des tentatives de connexion (429 après seuil).
- **CORS** restreint via `.env` (jamais `*` en production).
- **Audit trail** : chaque évènement sensible (connexion, accès refusé, etc.) est
  journalisé dans `audit_logs`. Les descriptions sont **filtrées** (aucun mot de
  passe / token / secret) et les tokens ne sont jamais stockés en clair (hash
  court via `session_ref`). Consultation réservée à HR/ADMIN via
  `/api/admin/audit-logs`.
- **Autorisation côté backend** : toute donnée sensible passe par
  `permission_service` (périmètre strict par rôle COLLAB / MANAGER / HR).

## 🧪 Tests (sécurité / traçabilité)

```bash
cd backend
python -m pytest -v   # tests sous app/tests/ (cf. pytest.ini)
```

La suite couvre :
- `test_security.py` — hachage, vérification, migration de hash, tokens, rate limiting
- `test_audit.py` — journalisation, filtrage anti-fuite, référence de session non réversible
- `test_permissions.py` — contrôle de rôle, accès admin, périmètre de données par rôle
- `test_auth_endpoints.py` — 401 sans token, login/logout, /auth/me, /auth/register, 429

Les tests utilisent une **base SQLite temporaire isolée** (jamais la base de
production) configurée dans `tests/conftest.py`.

## 📡 Principaux endpoints

| Méthode | Endpoint | Rôle requis | Description |
|--------|----------|-------------|-------------|
| GET | `/health` | public | Sonde de disponibilité |
| POST | `/api/auth/login` | public | Connexion (token de session) |
| POST | `/api/auth/register` | public | Inscription |
| GET | `/api/auth/me` | authentifié | Profil courant |
| POST | `/api/analyze-smart` | authentifié | Analyse SMART d'un objectif |
| POST | `/api/analyze-alignment` | authentifié | Analyse d'alignement stratégique |
| GET | `/api/manager/objectives` | MANAGER | Objectifs de l'équipe |
| GET | `/api/hr/analytics` | HR | Tableaux de bord analytiques |
| POST | `/api/import-excel-analyze` | COLLAB/MANAGER/HR | Import Excel + analyse en lot |
| GET | `/api/admin/audit-logs` | HR/ADMIN | Journal d'audit |

> La liste complète et interactive est disponible sur `/docs`.

## 🔧 Configuration

Toute la configuration se fait via le fichier `.env` (voir `.env.example`).
Aucun secret n'est codé en dur dans le code (`core/config.py` est l'unique source).

| Variable | Rôle |
|----------|------|
| `SECRET_KEY` | Clé secrète de l'application |
| `SESSION_DURATION_HOURS` | Durée de validité d'une session |
| `PBKDF2_ITERATIONS` | Coût du hachage des mots de passe |
| `MAX_LOGIN_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | Anti brute-force |
| `DATABASE_PATH` | Chemin de la base SQLite |
| `ALLOWED_ORIGINS` | Origines CORS autorisées |
| `OLLAMA_URL` / `OLLAMA_MODEL` | Configuration de l'IA locale |
| `SEED_*_PASSWORD` | Comptes de démonstration (dev uniquement) |
| `LDAP_*` / `SSO_*` | Réservé à la future intégration IAM bancaire |

## 🐛 Dépannage

- **« Ollama n'est pas démarré »** → `ollama serve`
- **« Modèle smart-qwen8 non trouvé »** → `ollama create smart-qwen8 -f Modelfile`
- **Frontend ne joint pas le backend** → vérifier le proxy `/api` dans
  `frontend/vite.config.ts` (cible `http://localhost:5001`) et que le backend tourne.

## 👥 Équipe — Groupe 03

- Lompo Bampalou Ernest
- Chaabi Taha
- Bajja Ilyas
- Taifouri Marwa
- Jadlaoui Marwen
- David

**Encadrement :** Mme Annoukoubi Maha (ECC)
**Entreprise :** BMCI — ABID Chaimaa, ESSAEGH Keltoum

---
*École Centrale Casablanca — Année académique 2024-2025*
