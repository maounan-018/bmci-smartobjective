# 🎯 ObjectifSMART-AI — BMCI

Application RH d'analyse des objectifs annuels selon la méthode **SMART**
(Spécifique, Mesurable, Atteignable, Réaliste, Temporel) et de leur **alignement
stratégique**, propulsée par une **IA locale** (Ollama). L'application aide
collaborateurs, managers et RH à évaluer la qualité des objectifs **sans jamais
faire sortir les données de l'infrastructure de la banque**.

> Version **3.0** — Frontend **Vue.js (JavaScript)**, backend **Python FastAPI**
> en architecture **MVC + SQLAlchemy ORM**, IA **Ollama** locale, sécurité et
> traçabilité renforcées. Le backend reste l'unique source de vérité.

---

## 📑 Table des matières

1. [Architecture globale](#1-architecture-globale)
2. [Structure du dépôt](#2-structure-du-dépôt)
3. [Pile technique](#3-pile-technique)
4. [Fonctionnalités](#4-fonctionnalités)
5. [Rôles & isolation des données](#5-rôles--isolation-des-données)
6. [Backend (FastAPI + SQLAlchemy)](#6-backend-fastapi--sqlalchemy)
7. [Frontend (Vue.js)](#7-frontend-vuejs)
8. [Module IA (Ollama)](#8-module-ia-ollama)
9. [Sécurité & traçabilité](#9-sécurité--traçabilité)
10. [Installation](#10-installation)
11. [Démarrage](#11-démarrage)
12. [Tests](#12-tests)
13. [Configuration (.env)](#13-configuration-env)
14. [Endpoints principaux](#14-endpoints-principaux)
15. [Dépannage](#15-dépannage)
16. [Évolutions prévues](#16-évolutions-prévues)
17. [Équipe](#17-équipe)

---

## 1. Architecture globale

```
┌───────────────────────┐     ┌──────────────────────────┐     ┌─────────────────────┐
│  Frontend Vue.js       │────▶│  Backend FastAPI (MVC)    │────▶│  Ollama (local)     │
│  Vite — :3000          │     │  Python — :5001           │     │  smart-qwen8        │
│  Pinia, vue-router     │     │  SQLAlchemy ORM           │     │  :11434             │
│  Chart.js              │     │  SQLite (objectifsmart.db)│     │  (jamais exposé)    │
└───────────────────────┘     └──────────────────────────┘     └─────────────────────┘
         │                                │                              ▲
         │  proxy /api  ───────────────▶ source de vérité                │
         └────────────────────────────────┴──────────────────────────────┘
                                          appel HTTP local
```

- **Le frontend ne connaît ni l'IA ni la base directement** : tout passe par les
  endpoints `/api/*` du backend (proxy Vite en développement).
- **Le backend est l'unique source de vérité** : authentification, autorisation,
  périmètre RBAC, appels IA, persistance.
- **L'IA tourne en local** : aucune donnée ne quitte la machine.

---

## 2. Structure du dépôt

```
bmci-smartobjective/
├── backend/                        # Backend FastAPI (MVC + SQLAlchemy)
│   ├── pytest.ini
│   ├── DOCUMENTATION.md            # Documentation technique du backend
│   ├── COURS_BACKEND_LIGNE_PAR_LIGNE.pdf   # Cours pédagogique (PDF)
│   ├── docs/
│   │   └── generate_course_pdf.py  # Générateur du cours PDF
│   └── app/
│       ├── main.py                 # Fabrique FastAPI + montage des routers
│       ├── core/                   # config (.env) + security (PBKDF2, tokens)
│       ├── database/               # SQLAlchemy : base, session, init_db
│       ├── models/                 # Modèles ORM (7 tables)
│       ├── repositories/           # TOUTES les requêtes (aucun SQL ailleurs)
│       ├── services/               # Logique métier (auth, hr, manager, ai, …)
│       ├── controllers/            # Routes FastAPI (fines, délèguent aux services)
│       ├── schemas/                # Schémas Pydantic
│       ├── auth/                   # Contrat IdentityProvider + providers/
│       ├── middlewares/            # Limitation de la taille des requêtes
│       ├── utils/                  # Helpers (calcul SMART, métadonnées requête)
│       └── tests/                  # pytest (32 tests sécurité / RBAC / import)
│
├── frontend/                       # Frontend Vue.js (JavaScript pur)
│   ├── package.json
│   ├── vite.config.js              # Proxy /api -> http://localhost:5001
│   ├── index.html
│   └── src/
│       ├── main.js                 # Point d'entrée Vue + Pinia + router
│       ├── App.vue
│       ├── router/index.js         # Routes (guards par rôle)
│       ├── guards/authGuard.js     # Vérification de session avant chaque route
│       ├── stores/authStore.js     # État global d'authentification (Pinia)
│       ├── services/               # apiService, authService, aiService
│       ├── views/                  # LoginView, CollaboratorDashboard,
│       │                           # ManagerDashboard, HrDashboard, SmartAnalysisView
│       ├── components/             # Navbar, SmartBadge, AlignmentChart
│       ├── layouts/                # DashboardLayout
│       └── utils/                  # permissions (UserRole, getDefaultPath), formatters
│
├── .env.example                    # Modèle de configuration
├── .gitignore                      # Ignore .env, *.db, node_modules, __pycache__
├── Modelfile                       # Définition du modèle Ollama smart-qwen8
├── requirements.txt                # Dépendances Python (backend)
├── start_app.bat / start_app.sh    # Démarrage tout-en-un (Windows / Unix)
└── README.md
```

> Le dossier `frontend/` est le **frontend officiel** (Vue.js, JavaScript pur).
> L'arborescence à la racine (`App.jsx`, `pages/`, `components/`, `services/`)
> est une **app React de référence** historique, également en JavaScript pur
> (migration TypeScript → JavaScript effectuée).

---

## 3. Pile technique

### Backend
| Composant | Choix | Rôle |
|---|---|---|
| Framework web | **FastAPI** | Routes, validation, OpenAPI |
| Serveur ASGI | **Uvicorn** | Exécution |
| ORM | **SQLAlchemy 2.0** | Modèles, requêtes, sessions |
| Base de données | **SQLite** (`objectifsmart.db`) | Persistance locale |
| Validation | **Pydantic v2** | Schémas d'entrée/sortie |
| IA | **Ollama** (`smart-qwen8`) | Modèle local |
| Excel | **openpyxl** | Lecture/écriture |
| PDF | **reportlab** | Génération de rapports |
| Tests | **pytest** + **httpx** | Tests d'intégration |

### Frontend
| Composant | Choix | Rôle |
|---|---|---|
| Framework | **Vue 3** (Composition API) | UI réactive |
| Build | **Vite** | Dev server + bundler |
| Router | **vue-router 4** | Navigation + guards par rôle |
| État global | **Pinia** | Store d'authentification |
| Graphiques | **Chart.js** + **vue-chartjs** | Dashboards |
| Icônes | **lucide-vue-next** | Iconographie |
| Styles | **Tailwind CSS** (CDN) | Mise en forme |

---

## 4. Fonctionnalités

- **Authentification & rôles** : login / register pour COLLAB, MANAGER, HR
  (logout, expiration de session, anti brute-force).
- **Objectifs personnels** : CRUD pour COLLAB, vue d'équipe pour MANAGER, vue
  globale agrégée pour HR.
- **Catalogue stratégique** : référentiel des objectifs d'entreprise (HR/MANAGER).
- **Analyse IA SMART** : évaluation des 5 critères (Spécifique, Mesurable,
  Atteignable, Réaliste, Temporel) + reformulations FR/EN + recommandations.
- **Alignement stratégique** : score d'alignement de chaque objectif avec le
  catalogue (top matches + écarts).
- **Imports Excel** : import des objectifs collaborateurs et stratégiques par RH,
  import individuel pour Collaborateur/Manager. **Drag & drop** + sélecteur natif.
- **Analyse en lot** (HR) : analyse SMART + alignement de N objectifs avec
  progression **SSE (server-sent events)**.
- **Tableaux de bord analytiques RH** : statistiques globales, évolutions
  mensuelles, distributions, points bloquants, comparaisons par entité /
  manager / période.
- **Exports** : Excel multi-feuilles et PDF synthétiques (Manager + RH).
- **Audit trail** : journalisation des évènements sensibles + filtrage anti-fuite.
- **Module IA évolutif** : prêt à challenger et améliorer automatiquement les
  objectifs (les reformulations sont déjà produites par le modèle).

---

## 5. Rôles & isolation des données

| Rôle | Périmètre | Inscription publique |
|---|---|---|
| **COLLAB** | Ses propres objectifs uniquement (manager obligatoire à l'inscription) | ✅ |
| **MANAGER** | Lui-même + son équipe (`manager_id = lui`), excluant les imports RH | ✅ (sans manager) |
| **HR** | Vue globale agrégée (uniquement les imports RH : `data_scope='HR'` ou `import_batch_id LIKE 'obj-%'`) | ✅ (sans manager) |
| **ADMIN** | Réservé à l'évolution future ; aujourd'hui HR fait office d'admin pour l'audit | ❌ |

> **Isolation stricte** : les analyses sont stockées dans **trois tables
> physiquement séparées** (`hr_analysis_results`, `manager_analysis_results`,
> `collab_analysis_results`). Une analyse RH n'est jamais visible côté Manager
> et inversement. Le marquage `data_scope` sur les objectifs renforce ce
> cloisonnement.

---

## 6. Backend (FastAPI + SQLAlchemy)

Le backend suit une **architecture en couches** stricte. Chaque couche ne parle
qu'à la couche immédiatement inférieure.

```
controllers  →  services  →  repositories  →  models  →  database
(routes)        (logique)    (requêtes)       (ORM)      (engine)
```

**Règles d'or :**
- Aucun **SQL** hors des `repositories/`.
- Aucune **logique métier** dans les `controllers/` (ils appellent un service).
- Aucun **secret** en dur : tout passe par `core/config.py` (`.env`).

### Couches

| Dossier | Rôle |
|---|---|
| `app/core/` | `config` (settings depuis .env), `security` (PBKDF2, tokens, rate-limit) |
| `app/database/` | `base` (DeclarativeBase), `session` (engine + `db_session`), `init_db` |
| `app/models/` | 7 modèles ORM : User, Session, Objective, CompanyObjective, AnalysisResult (HR/Manager/Collab), AuditLog, HRImport |
| `app/repositories/` | Toutes les requêtes (ORM + `text()` pour reporting RH) |
| `app/services/` | auth, user, objective, manager, hr, ai, audit, export, excel_import, permission |
| `app/controllers/` | auth, admin, objective, manager, hr, ai |
| `app/schemas/` | auth, user, objective, analysis, hr (Pydantic) |
| `app/auth/` | `IdentityProvider` (ABC) + `providers/local_provider.py` + `providers/ldap_provider.py` (squelette IAM bancaire) |
| `app/middlewares/` | `request_size` (anti-DoS, 413 si > 20 Mo) |
| `app/utils/` | helpers purs (score SMART, `request_meta`) |
| `app/tests/` | 32 tests pytest (sécurité, audit, RBAC, auth, import Excel) |

> 📘 **Documentation détaillée** : `backend/DOCUMENTATION.md` (référence
> technique) et `backend/COURS_BACKEND_LIGNE_PAR_LIGNE.pdf` (cours pédagogique
> ligne par ligne pour comprendre et faire évoluer le code).

---

## 7. Frontend (Vue.js)

Frontend **Vue 3** en JavaScript pur (Composition API), build avec **Vite**.

### Découpage

| Dossier / fichier | Rôle |
|---|---|
| `src/main.js` | Point d'entrée : crée l'app, monte Pinia, branche le router |
| `src/App.vue` | Composant racine (`<router-view />`) |
| `src/router/index.js` | Routes (login, dashboards par rôle) + meta `roles` |
| `src/guards/authGuard.js` | Avant chaque route : valide la session via `/api/auth/me`, redirige selon le rôle |
| `src/stores/authStore.js` | Store Pinia : utilisateur courant, login/logout, persistance localStorage |
| `src/services/apiService.js` | Appels REST métier (objectifs, manager, hr, analytics, exports, imports) |
| `src/services/authService.js` | Login / register / logout / `/me` + helpers d'authentification |
| `src/services/aiService.js` | Wrappers analyse SMART / alignement |
| `src/utils/permissions.js` | `UserRole` (COLLAB/MANAGER/HR), `getDefaultPath(role)` |
| `src/utils/formatters.js` | Formatages dates, scores, libellés |
| `src/layouts/DashboardLayout.vue` | Layout commun (navbar, slot principal) |
| `src/components/Navbar.vue` | Barre de navigation (liens par rôle) |
| `src/components/SmartBadge.vue` | Badge visuel d'un sous-critère SMART |
| `src/components/AlignmentChart.vue` | Donut Chart.js d'alignement |
| `src/views/LoginView.vue` | Sélection du rôle + login/register |
| `src/views/CollaboratorDashboard.vue` | Mes objectifs + import CSV/Excel |
| `src/views/ManagerDashboard.vue` | Équipe + analyses + import Excel |
| `src/views/HrDashboard.vue` | Imports stratégie/objectifs + analyse en lot SSE + analytics + exports |
| `src/views/SmartAnalysisView.vue` | Analyse SMART personnelle (HR) |

### Connexion au backend

- **Vite proxifie** `/api` → `http://localhost:5001` (cf. `vite.config.js`) →
  pas de souci CORS en développement.
- **Authentification** : token Bearer dans `Authorization`, géré par
  `authService.authFetch(...)` qui purge le token et redirige sur 401.
- **Uploads** : `<input type="file">` natif **+ drag & drop** depuis l'OS
  (contourne la popup « Charger depuis mobile » de Microsoft Edge) sur les
  3 dashboards.
- **Analyse en lot** (HR) : lecture du flux **SSE** `text/event-stream` ligne
  par ligne (`data: ...`).

---

## 8. Module IA (Ollama)

L'IA tourne **en local** avec Ollama et un modèle dédié `smart-qwen8` (cf.
`Modelfile`). Le backend appelle Ollama via HTTP (`OLLAMA_URL` du `.env`).

- **Analyse SMART** : renvoie `{S, M, A, R, T, overall, confidence, issues,
  rewrite_fr, rewrite_en}`.
- **Analyse d'alignement** : renvoie `{alignment_score, top_matches, gaps}`.
- **Heuristiques de cohérence** : le backend corrige les incohérences du modèle
  (ex. `M=true` sans indicateur chiffré → remis à `false`, `overall` recalculé).
- **Robustesse** : extraction tolérante du JSON, codes HTTP explicites
  (503 si Ollama éteint, 504 si timeout).

> Aucune donnée ne quitte l'infrastructure : le modèle s'exécute sur la même
> machine que le backend.

---

## 9. Sécurité & traçabilité

| Mesure | Mise en œuvre |
|---|---|
| **Mots de passe** | PBKDF2-HMAC-SHA256 salé (`secrets.token_bytes(16)`, coût configurable) |
| **Vérification** | À temps constant (`hmac.compare_digest`) |
| **Migration auto** | Détection du legacy SHA-256 → rehash transparent à la connexion |
| **Sessions** | Tokens aléatoires (`secrets.token_urlsafe(32)`), expiration configurable, session unique |
| **Anti brute-force** | Blocage 429 après `MAX_LOGIN_ATTEMPTS` (défaut 5) sur `LOGIN_LOCKOUT_MINUTES` (défaut 15) |
| **CORS** | Origines explicites via `.env`, **wildcard `*` interdit** (échec démarrage) |
| **Taille requête** | Middleware 413 au-delà de `MAX_REQUEST_SIZE_MB` (défaut 20 Mo) |
| **RBAC** | `permission_service` centralise : `require_role`, `require_admin`, `check_collab_access`, `check_manager_access`, `get_accessible_user_ids` |
| **Anti-escalade** | Whitelist `{COLLAB, MANAGER, HR}` à l'inscription ; toute autre valeur → COLLAB. Le rôle ADMIN n'est jamais créé via `/auth/register` |
| **Audit trail** | Tous les évènements sensibles journalisés (login/logout/access denied/session expired) avec **filtrage** des descriptions (`password`, `token`, `secret`, … → `[DESCRIPTION FILTRÉE]`) ; les tokens ne sont jamais stockés en clair (hash court `session_ref`) |
| **Consultation audit** | Réservée HR/ADMIN via `/api/admin/audit-logs` |

---

## 10. Installation

### Prérequis

| Outil | Version |
|---|---|
| **Python** | ≥ 3.10 (testé 3.12) |
| **Node.js** | ≥ 18 |
| **Ollama** | dernière version ([installer](https://ollama.com)) |

### 1) Cloner et entrer dans le projet
```bash
git clone https://github.com/LOMPO-ERNEST/bmci-smartobjective.git
cd bmci-smartobjective
```

### 2) Backend Python
```bash
pip install -r requirements.txt
```

### 3) Frontend Vue
```bash
cd frontend && npm install && cd ..
```

### 4) Modèle IA Ollama
```bash
ollama create smart-qwen8 -f Modelfile
```

### 5) Configuration
```bash
cp .env.example .env
# Générer une SECRET_KEY robuste :
python -c "import secrets; print(secrets.token_hex(32))"
# → coller le résultat dans SECRET_KEY du fichier .env
```

> Le `.env` doit aussi être présent (ou symlinké) **à la racine** et **dans
> `backend/`** (car `load_dotenv` lit depuis le CWD courant). Le plus simple :
> `cp .env backend/.env`.

> ⚠️ Ne jamais committer `.env` (déjà dans `.gitignore`).

---

## 11. Démarrage

### Option A — Démarrage tout-en-un
```bash
# Windows
start_app.bat

# Linux / macOS
./start_app.sh
```
Lance Ollama, le backend (port 5001) et le frontend (port 3000) en parallèle.

### Option B — Trois terminaux manuels

**Terminal 1 — Ollama**
```bash
ollama serve
```

**Terminal 2 — Backend FastAPI (port 5001)**
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

**Terminal 3 — Frontend Vue (port 3000)**
```bash
cd frontend
npm run dev
```

### Accès
- **Application** : http://localhost:3000
- **API Swagger** : http://localhost:5001/docs
- **Health check** : http://localhost:5001/health

---

## 12. Tests

### Backend (pytest)
```bash
cd backend
python -m pytest -v
```
**32 tests verts**. Base SQLite **temporaire isolée** (jamais la production),
schéma créé via l'ORM (`init_db`) dans `app/tests/conftest.py`.

Couverture :
- `test_security.py` — PBKDF2, vérif, legacy, tokens, rate-limit, rejet 413
- `test_audit.py` — écriture/lecture, filtrage anti-fuite, `session_ref`
- `test_permissions.py` — RBAC, périmètres par rôle
- `test_auth_endpoints.py` — 401, login/register (COLLAB/MANAGER/HR autorisés,
  ADMIN ramené à COLLAB), rate-limit 429
- `test_hr_import.py` — mots de passe aléatoires distincts, pas de recréation
  d'utilisateur existant

### Frontend (build de production)
```bash
cd frontend
npm run build       # validation : ~1600 modules transformés
```

---

## 13. Configuration (`.env`)

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | Clé secrète de l'application (64 hex aléatoires) |
| `SESSION_DURATION_HOURS` | Durée de validité d'une session (défaut 24) |
| `PBKDF2_ITERATIONS` | Coût du hachage (défaut 200 000) |
| `MAX_LOGIN_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | Anti brute-force (défaut 5 / 15) |
| `MAX_REQUEST_SIZE_MB` | Limite uploads (défaut 20 Mo) |
| `DATABASE_PATH` | Chemin SQLite (défaut `objectifsmart.db`) |
| `ALLOWED_ORIGINS` | Origines CORS (obligatoire ; `*` interdit) |
| `OLLAMA_URL` / `OLLAMA_MODEL` | Configuration de l'IA locale |
| `AUTH_PROVIDER` | `local` (défaut) ou `ldap` (à activer après intégration IAM) |
| `LDAP_*` / `SSO_*` | Réservé à la future intégration IAM bancaire |
| `SEED_*_PASSWORD` | Comptes de démonstration (dev uniquement) |

---

## 14. Endpoints principaux

| Méthode | Endpoint | Rôle requis | Description |
|---|---|---|---|
| GET | `/health` | public | Sonde de disponibilité |
| GET | `/api/managers` | public | Liste publique des managers (id/name/team) pour l'inscription COLLAB |
| POST | `/api/auth/register` | public | Inscription (COLLAB, MANAGER ou HR) |
| POST | `/api/auth/login` | public | Connexion (token de session) |
| POST | `/api/auth/logout` | authentifié | Déconnexion |
| GET | `/api/auth/me` | authentifié | Profil courant |
| GET | `/api/admin/audit-logs` | HR/ADMIN | Journal d'audit |
| GET/POST | `/api/objectives` | authentifié | Lister / créer un objectif |
| GET/PUT/DELETE | `/api/objectives/{id}` | propriétaire/HR | Lire / modifier / supprimer |
| GET/POST | `/api/company-objectives` | public / MANAGER-HR | Catalogue stratégique |
| GET | `/api/team/members`, `/api/team/stats` | MANAGER/HR | Équipe générique |
| GET | `/api/manager/*` | MANAGER | Dashboard, équipe, analyses, export |
| GET | `/api/collab/analysis-results` | COLLAB | Analyses privées |
| POST | `/api/analyze-smart`, `/api/analyze-alignment` | authentifié | Analyse IA unitaire |
| POST | `/api/scan-excel`, `/api/import-excel-analyze`, `/api/import-excel-export` | COLLAB/MANAGER/HR | Pipeline Excel intelligent |
| POST | `/api/hr/import-strategy`, `/api/hr/import-objectives` | HR | Imports Excel RH |
| POST | `/api/hr/analyze-batch` | HR | Analyse en lot **SSE** |
| GET | `/api/hr/analytics`, `/api/hr/objectives-details`, `/api/hr/imports` | HR | Tableaux de bord & historique |
| GET | `/api/hr/export-excel`, `/api/hr/export-pdf`, `/api/manager/export` | HR / MANAGER | Rapports |

> Liste complète interactive sur **`/docs`** (Swagger UI).

---

## 15. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| Backend refuse de démarrer (`ALLOWED_ORIGINS doit être défini`) | `.env` manquant ou `ALLOWED_ORIGINS` vide / `*` | Créer `.env` (et le copier dans `backend/`) avec `ALLOWED_ORIGINS=http://localhost:3000` |
| « Ollama n'est pas démarré » | Service Ollama hors ligne | `ollama serve` |
| « Modèle smart-qwen8 non trouvé » | Modèle non créé | `ollama create smart-qwen8 -f Modelfile` |
| Frontend voit 404 sur `/api/*` | Backend pas sur :5001 ou proxy KO | Vérifier `frontend/vite.config.js` (target = `http://localhost:5001`) et que le backend tourne |
| Erreur d'upload « payload too large » | Fichier > 20 Mo | Augmenter `MAX_REQUEST_SIZE_MB` dans `.env` |
| Edge ouvre la popup « Charger depuis mobile » | Fonctionnalité Edge | Glisser-déposer le fichier sur la zone (drag & drop intégré) ou désactiver dans `edge://settings` |
| Inscription HR/MANAGER : « Sélection du manager obligatoire » | Backend > 9006b6d ancien | Mettre à jour le backend (la whitelist élargie est sur la branche `mvc-sqlalchemy-refactor`) |

---

## 16. Évolutions prévues

- **LDAP / SSO** (intégration IAM bancaire) — `LDAPProvider` est déjà un
  squelette ; bascule via `AUTH_PROVIDER=ldap` sans modifier les
  services/controllers.
- **Rôle `ADMIN` dédié** (aujourd'hui HR fait office d'admin).
- **Endpoint administratif** pour créer/désactiver des comptes (au-delà de la
  whitelist d'inscription publique).
- **Module IA étendu** : challenge et amélioration interactive des objectifs.
- **Migrations** : introduction d'Alembic au-delà du `create_all` quand le
  schéma évoluera.

---

## 17. Équipe

**Groupe 03**
- Lompo Bampalou Ernest
- Chaabi Taha
- Bajja Ilyas
- Taifouri Marwa
- Jadlaoui Marwen
- David

**Encadrement :** Mme Annoukoubi Maha (ECC)
**Entreprise :** BMCI — ABID Chaimaa, ESSAEGH Keltoum

---
$root = "C:\bmci_objective\BMCI"; $ok = 0; $warn = 0; $err = 0
function Ck { param($p,$kw,$ml=3); $r=$p.Replace($root,"").TrimStart("\"); if(-not(Test-Path $p)){Write-Host "  [MANQUANT] $r" -f Red; $script:err++; return}; $l=Get-Content $p -EA SilentlyContinue; $c=if($l){$l.Count}else{0}; if($c -lt $ml){Write-Host "  [TRONQUE $c lignes] $r" -f Yellow; $script:warn++; return}; if($kw){$f=$false; foreach($k in $kw){if($l|Select-String $k -Quiet){$f=$true;break}}; if(-not $f){Write-Host "  [INCOMPLET] $r ($c lignes)" -f Yellow; $script:warn++; return}}; Write-Host "  [OK $c lignes] $r" -f Green; $script:ok++ }
Write-Host "`n=== DIAGNOSTIC BMCI ===" -f Cyan
Write-Host "`n-- DOSSIERS --" -f White
@("backend\app","backend\app\controllers","backend\app\services","backend\app\models","backend\app\schemas","backend\app\core","backend\app\database","backend\app\middlewares","frontend\src","frontend\src\views","frontend\src\stores","frontend\src\services","frontend\src\router") | % { $d="$root\$_"; $r=$_.TrimStart("\"); if(Test-Path $d){Write-Host "  [OK] $r" -f Green;$ok++}else{Write-Host "  [MANQUANT] $r" -f Red;$err++} }
Write-Host "`n-- BACKEND PRINCIPAL --" -f White
Ck "$root\backend\app\main.py" @("create_app","app = create_app") 20
Ck "$root\backend\app\core\config.py" @("ALLOWED_ORIGINS","Settings") 30
Ck "$root\backend\app\core\security.py" @("hash_password","verify_password") 10
Ck "$root\backend\app\database\init_db.py" @("init_db","Base.metadata") 10
Ck "$root\requirements.txt" @("fastapi","uvicorn") 5
Write-Host "`n-- CONTROLEURS --" -f White
Ck "$root\backend\app\controllers\auth_controller.py" @("router","APIRouter") 10
Ck "$root\backend\app\controllers\hr_controller.py" @("router","APIRouter") 10
Ck "$root\backend\app\controllers\manager_controller.py" @("router","APIRouter") 10
Ck "$root\backend\app\controllers\objective_controller.py" @("router","APIRouter") 10
Ck "$root\backend\app\controllers\ai_controller.py" @("router","APIRouter") 10
Ck "$root\backend\app\controllers\admin_controller.py" @("router","APIRouter") 10
Write-Host "`n-- SERVICES --" -f White
Ck "$root\backend\app\services\auth_service.py" @("def login","def register") 20
Ck "$root\backend\app\services\hr_service.py" @("def ") 20
Ck "$root\backend\app\services\objective_service.py" @("def ") 20
Ck "$root\backend\app\services\manager_service.py" @("def ") 20
Ck "$root\backend\app\services\ai_service.py" @("def ","ollama") 20
Ck "$root\backend\app\services\user_service.py" @("def ") 10
Ck "$root\backend\app\services\audit_service.py" @("def ") 10
Ck "$root\backend\app\services\export_service.py" @("def ") 10
Ck "$root\backend\app\services\permission_service.py" @("def ") 10
Ck "$root\backend\app\services\excel_import_service.py" @("def ") 10
Write-Host "`n-- MODELES --" -f White
Ck "$root\backend\app\models\user.py" @("class User","Column") 10
Ck "$root\backend\app\models\objective.py" @("class","Column") 10
Ck "$root\backend\app\models\session.py" @("class","Column") 10
Ck "$root\backend\app\models\audit_log.py" @("class","Column") 10
Ck "$root\backend\app\models\company_objective.py" @("class","Column") 10
Ck "$root\backend\app\models\hr_import.py" @("class","Column") 10
Ck "$root\backend\app\models\analysis_result.py" @("class","Column") 10
Write-Host "`n-- SCHEMAS --" -f White
Ck "$root\backend\app\schemas\auth_schema.py" @("class","BaseModel") 10
Ck "$root\backend\app\schemas\hr_schema.py" @("class","BaseModel") 10
Ck "$root\backend\app\schemas\objective_schema.py" @("class","BaseModel") 10
Ck "$root\backend\app\schemas\user_schema.py" @("class","BaseModel") 10
Write-Host "`n-- ENV --" -f White
$ep="$root\backend\.env"; if(Test-Path $ep){$ec=Get-Content $ep -Raw; if($ec -match "ALLOWED_ORIGINS"){Write-Host "  [OK] backend\.env" -f Green;$ok++}else{Write-Host "  [INCOMPLET] backend\.env - ALLOWED_ORIGINS manquant!" -f Yellow;$warn++}}else{Write-Host "  [MANQUANT] backend\.env - BACKEND NE PEUT PAS DEMARRER!" -f Red;$err++}
Write-Host "`n-- FRONTEND --" -f White
Ck "$root\frontend\index.html" @("div","app") 5
Ck "$root\frontend\package.json" @("vue","vite") 5
Ck "$root\frontend\vite.config.js" @("defineConfig","vue") 5
Ck "$root\frontend\src\main.js" @("createApp","App") 5
Ck "$root\frontend\src\views\LoginView.vue" @("login","password") 20
Ck "$root\frontend\src\views\HrDashboard.vue" @("template","script") 30
Ck "$root\frontend\src\views\ManagerDashboard.vue" @("template","script") 30
Ck "$root\frontend\src\views\CollaboratorDashboard.vue" @("template","script") 30
Ck "$root\frontend\src\stores\authStore.js" @("defineStore","user") 10
Ck "$root\frontend\src\services\api.js" @("fetch","localhost") 10
Ck "$root\frontend\src\router\index.js" @("createRouter","routes") 10
$nm="$root\frontend\node_modules"; if(Test-Path $nm){$nc=(Get-ChildItem $nm -Directory -EA SilentlyContinue|Measure-Object).Count; Write-Host "  [OK] node_modules ($nc paquets)" -f Green;$ok++}else{Write-Host "  [MANQUANT] node_modules - fais: cd frontend && npm install" -f Red;$err++}
Ck "$root\Modelfile" @("FROM qwen","SYSTEM") 5
Write-Host "`n=========================" -f Cyan
Write-Host "  OK=$ok  INCOMPLET=$warn  MANQUANT=$err" -f White
if($err -gt 0){Write-Host "  FICHIERS MANQUANTS - envoie le resultat!" -f Red}elseif($warn -gt 0){Write-Host "  FICHIERS INCOMPLETS - envoie le resultat!" -f Yellow}else{Write-Host "  TOUT EST OK!" -f Green}
*École Centrale Casablanca — Année académique 2024-2025*
