# 🎯 ObjectifSMART-AI — Objectifs annuels assistés par IA locale

[![CI](https://github.com/maounan-018/bmci-smartobjective_DMD_V1/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/maounan-018/bmci-smartobjective_DMD_V1/actions/workflows/ci.yml)

Plateforme web d'**évaluation SMART** (Spécifique, Mesurable, Atteignable,
Réaliste, Temporel) et d'**alignement stratégique** des objectifs annuels pour
un grand groupe bancaire. Trois espaces (**Collaborateur**, **Manager**,
**HRBP**) sur un parcours cohérent : saisie des objectifs, analyse IA SMART,
score d'alignement, imports Excel, dashboards analytiques, Coach IA
conversationnel, exports PDF/Excel pour le COMEX.

> **Stack** · Vue 3 / Vite / Tailwind — FastAPI (MVC, SQLAlchemy 2.0) — Ollama
> local (Qwen3, BGE-M3) — SSO SAML 2.0 (ADFS / Entra ID) — SQLite dev,
> PostgreSQL prod — IA 100 % locale, aucune donnée exfiltrée.

---

## ✨ Points forts

- **IA entièrement locale** — modèle Ollama `smart-qwen8` construit à partir
  d'un `Modelfile` (Qwen3-8B avec prompts métier bancaires), embeddings
  `bge-m3`. Aucune API externe, aucune donnée ne quitte l'infrastructure.
- **Analyse SMART rigoureuse** — évaluation des 5 critères avec reformulations
  FR/EN et score d'alignement stratégique (top matches + écarts par rapport au
  catalogue d'entreprise).
- **Coach IA conversationnel** — accompagnement SMART pas-à-pas et réponses
  ancrées sur la base de connaissances personnelle (RAG local).
- **Base de connaissances privée** — chaque utilisateur téléverse ses documents
  (PDF, Word, Excel, texte) ; **OCR automatique** pour les PDF scannés via
  `rapidocr-onnxruntime`. Isolation stricte : chacun n'accède qu'à ses propres
  documents via `uploaded_by`.
- **SSO SAML 2.0 production-grade** — intégration ADFS / Entra ID avec
  assertions signées RSA-SHA256, JIT provisioning, désactivation automatique
  de la connexion locale en mode SSO réel. Mode simulation pour les
  environnements de dev.
- **Sécurité bancaire par conception** — PBKDF2, tokens hashés en base,
  cookies HttpOnly + CSRF double-submit, CORS strict, en-têtes CSP/HSTS,
  anti brute-force par email+IP, middleware anti-DoS, audit trail filtré.
- **Isolation RBAC ligne-à-ligne** — trois tables séparées pour les analyses
  (`hr_/manager_/collab_analysis_results`), cloisonnement renforcé par
  `data_scope`. Une analyse RH n'est jamais visible côté Manager.
- **Industrialisation** — pre-commit (ruff + hygiène), CI GitHub Actions
  (lint, 103 tests backend, build Vite, scan secrets, audit deps), config
  gunicorn multi-worker pour la prod.

---

## 🏛️ Architecture

```
┌──────────────────────┐          ┌───────────────────────┐          ┌──────────────────┐
│  Frontend Vue 3      │ ───────▶ │  Backend FastAPI      │ ───────▶ │  Ollama (local)  │
│  Vite · Tailwind     │  /api/*  │  MVC · SQLAlchemy 2.0 │ generate │  smart-qwen8     │
│  Pinia · Chart.js    │          │  JSON / SSE           │  embed   │  bge-m3          │
└──────────────────────┘          └───────────┬───────────┘          └──────────────────┘
                                              │                      :11434 jamais exposé
                                 ┌────────────┴─────────────┐
                                 ▼                          ▼
                     ┌──────────────────────┐    ┌──────────────────────────┐
                     │  SQLite + sqlite-vec │    │  PostgreSQL (prod)       │
                     │  (dev local)         │ OR │  recommandé au-delà      │
                     └──────────────────────┘    └──────────────────────────┘
```

**Principes directeurs** :

1. Le frontend ne connaît ni l'IA ni la base — tout passe par `/api/*` (proxy
   Vite en dev).
2. Le backend est l'unique source de vérité : auth, RBAC, orchestration IA,
   persistance, audit.
3. L'IA tourne en local (`:11434` jamais exposé). Aucune donnée ne quitte la
   machine.
4. Confidentialité par conception : trois tables d'analyses séparées,
   documents RAG isolés par propriétaire.

---

## 🚀 Démarrage rapide

Double-cliquez sur **`LANCER_APP.bat`** (Windows) ou lancez **`./start_app.sh`**
(Linux/macOS). Le script vérifie les prérequis, installe les dépendances
manquantes, démarre Ollama (`:11434`), le backend FastAPI (`:5001`) et le
frontend Vite (`:3000`), puis ouvre le navigateur.

**Prérequis (une fois)** :

- Python ≥ 3.10 (testé 3.12)
- Node.js ≥ 18
- [Ollama](https://ollama.com/) + modèle de base : `ollama pull qwen3:8b`
- Modèle métier dédié : `ollama create smart-qwen8 -f Modelfile`

**Vérification de l'environnement** : `python verif_projet.py` (ou double-clic
sur `VERIFIER.bat`) diagnostique Python, dépendances, `sqlite-vec`, Ollama,
modèles, fichiers et ports — et donne pour chaque manque la commande qui
répare.

**Mode manuel (3 terminaux)** :

```bash
ollama serve                                                      # 1
cd backend && python -m uvicorn app.main:app --port 5001 --reload # 2
cd frontend && npm run dev                                        # 3
```

### Accès

- Application : http://localhost:3000
- API Swagger : http://localhost:5001/docs
- Health check : http://localhost:5001/health

### Comptes de démonstration

Les comptes démo (`SEED_DEMO_ACCOUNTS=true`) sont créés au démarrage avec des
mots de passe **injectés par variable d'environnement** (`SEED_*_PASSWORD` dans
`backend/.env.local`, jamais commité). Ils sont **automatiquement désactivés
en SSO réel** et doivent être retirés en production.

---

## 🤖 Pile IA

| Composant | Modèle | Rôle |
|---|---|---|
| Analyse SMART & alignement | `smart-qwen8` (construit depuis `Modelfile`, base Qwen3-8B) | Évaluation des 5 critères + reformulations FR/EN |
| Coach IA conversationnel | `smart-qwen8` | Accompagnement pas-à-pas + réponses ancrées sur le RAG |
| Embeddings RAG | `bge-m3` (1024 dim) | Indexation des documents utilisateur |
| Extraction documents | PyMuPDF (PDF) · openpyxl (Excel) · python-docx (Word) · rapidocr-onnxruntime (OCR local) | Alimentation du RAG |

Les quotas IA sont bornés par utilisateur (`AI_RATE_LIMIT_MAX` / fenêtre
`AI_RATE_LIMIT_WINDOW_SECONDS`), avec audit des dépassements et messages
d'erreur génériques côté client.

---

## 🔐 Sécurité & secrets

Rien de sensible n'est versionné :

- `backend/.env` : config de dev (ports, flags, CORS) — **sans aucun secret**.
- `backend/.env.local` : **gitignored**, héberge les mots de passe seed, les
  certificats SAML, `DATABASE_URL` prod, etc.
- Les comptes de démonstration existent uniquement en base de dev seedée ;
  leurs mots de passe sont injectés par environnement, jamais commités dans
  le bundle ni le code.
- Historique git scanné en continu par `gitleaks` (job CI dédié).

**Authentification** :

- **SSO SAML 2.0** (production) : ADFS / Entra ID, assertions signées
  RSA-SHA256, token jamais dans l'URL (échange via code à usage unique),
  JIT provisioning avec rôle déduit des groupes d'annuaire.
- **Local (fallback)** : PBKDF2-HMAC-SHA256 (200 000 itérations), vérification
  à temps constant, migration automatique des hash legacy.
- **Pas d'inscription publique** — comptes créés via SSO/JIT ou provisionnés
  par admin (`python create_user.py --email ... --role ... --password ...`).

**Transport** : cookie HttpOnly + Secure + SameSite + CSRF double-submit, ou
Bearer `sessionStorage` pour clients non-navigateur.

**Isolation RBAC** :

| Rôle | Périmètre |
|---|---|
| COLLAB | Ses propres objectifs uniquement |
| MANAGER | Lui-même + équipe (`manager_id = lui`), hors imports RH |
| HR / HRBP | Vue globale agrégée (`data_scope='HR'`), accès audit |
| ADMIN | Réservé évolution future ; HR fait office d'admin |

---

## ⚙️ Qualité & process dev

| Outil | Commande | Rôle |
|---|---|---|
| **pre-commit** | `pre-commit install` | Hooks locaux : ruff + hygiène (yaml, large files, debug statements, private keys) |
| **ruff** | `ruff check . && ruff format .` | Lint + format Python (black-compatible) |
| **pytest** | `cd backend && pytest` | **103 tests** (sécurité, RBAC, SSO SAML, auth, RAG, Coach, import Excel) |
| **CI** | GitHub Actions sur chaque push/PR vers `main` | 3 jobs parallèles : backend, frontend, security |

---

## 🏭 Mise en production

En dev : `uvicorn app.main:app --reload`.

En prod :

1. **Variables d'environnement** dans `backend/.env.local` :
   ```ini
   ENV=production
   ALLOWED_ORIGINS=https://<url-interne-banque>
   SEED_DEMO_ACCOUNTS=false
   ```
   En `production` + SSO configuré, la connexion locale et les comptes démo
   sont automatiquement désactivés.

2. **SSO réel** : `pip install -r requirements-saml.txt` puis renseigner
   `SAML_SP_*` / `SAML_IDP_*` dans `.env.local`. Transmettre à la DSI l'URL
   des métadonnées SP : `/api/auth/saml/metadata`. Détails dans
   [`SSO_SAML.md`](SSO_SAML.md).

3. **HTTPS** via reverse proxy (nginx / IIS) portant le certificat TLS
   interne banque. Indispensable : les cookies `Secure` et HSTS ne sont
   actifs qu'en HTTPS.

4. **Serveur applicatif** : `gunicorn -c backend/gunicorn.conf.py app.main:app`
   — plusieurs `UvicornWorker` (formule `CPU*2+1`, override `WEB_CONCURRENCY`),
   timeouts adaptés aux traitements RAG/OCR longs, recyclage préventif.

5. **Base PostgreSQL** recommandée au-delà de SQLite pour la charge
   concurrente. Bascule par `DATABASE_URL=postgresql://…`.

6. **Comptes** : provisionner via `create_user.py` (fallback) ou laisser le
   JIT SSO créer au 1ᵉʳ login.

7. **Sauvegardes + supervision** (logs structurés JSON, alertes) et
   **validation sécu DSI** (pentest).

Guide pas-à-pas complet : [`DEPLOIEMENT.md`](DEPLOIEMENT.md).

---

## 🗂️ Structure du dépôt

```
.
├── .pre-commit-config.yaml       # Hooks locaux (ruff, hygiène)
├── .github/workflows/ci.yml      # CI : lint + tests + build + scan sécurité
├── LANCER_APP.bat                # Démarrage tout-en-un (Windows)
├── start_app.sh                  # Démarrage tout-en-un (Linux/macOS)
├── VERIFIER.bat                  # Diagnostic pré-lancement (Python/Ollama/ports)
├── Modelfile                     # Définition Ollama smart-qwen8 (REQUIS pour l'IA)
├── pyproject.toml                # Config ruff + pytest
├── requirements.txt              # Dépendances Python
├── requirements-saml.txt         # Dépendances SSO SAML (optionnel)
├── SSO_SAML.md                   # Guide SSO : simulation → réel → retrait
├── DEPLOIEMENT.md                # Guide déploiement complet
├── backend/                      # FastAPI (MVC + SQLAlchemy 2.0)
│   ├── .env                      #   Config de dev (sans secret)
│   ├── gunicorn.conf.py          #   Serveur de production
│   ├── create_user.py            #   Outil admin : créer comptes (rôle inclus)
│   └── app/{auth,controllers,core,database,middlewares,
│           models,repositories,schemas,services,utils,tests}
└── frontend/                     # Vue 3 (JavaScript, Vite, Pinia, Tailwind)
    ├── vite.config.js            #   Proxy /api → http://localhost:5001
    └── src/{components,guards,layouts,router,services,stores,utils,views}
```

---

## 🧪 Endpoints principaux

| Méthode | Endpoint | Rôle | Description |
|---|---|---|---|
| GET | `/health` | public | Sonde de disponibilité |
| POST | `/api/auth/login` | public | Connexion locale (cookie de session) |
| GET | `/api/auth/saml/*` | public | SSO (status, login, acs, metadata, exchange) |
| POST | `/api/auth/logout` | authentifié | Déconnexion |
| GET | `/api/auth/me` | authentifié | Profil courant |
| GET/POST | `/api/objectives` | authentifié | Objectifs personnels |
| GET/POST | `/api/company-objectives` | MANAGER/HR | Catalogue stratégique |
| GET | `/api/manager/*` | MANAGER | Dashboard, équipe, analyses, export |
| POST | `/api/analyze-smart`, `/api/analyze-alignment` | authentifié | Analyse IA |
| POST | `/api/chat-coach` | COLLAB/MANAGER/HR | Coach IA conversationnel (RAG privé) |
| GET/POST/DELETE | `/api/rag/documents` | COLLAB/MANAGER/HR | Base de connaissances personnelle |
| POST | `/api/hr/import-*`, `/api/hr/analyze-batch` | HR | Imports Excel + analyse SSE |
| GET | `/api/hr/analytics`, `/api/hr/export-*` | HR | Analytics & rapports PDF/Excel |
| GET | `/api/admin/audit-logs` | HR/ADMIN | Journal d'audit |

Liste complète interactive sur `/docs` (Swagger UI).

---

## 📜 Crédits & licences

Modèles IA : licences respectives (Qwen 3 · BGE-M3). Librairies : licences
open-source respectives (voir `requirements.txt` et `frontend/package.json`).
Code applicatif : usage personnel / démonstration.

---

*École Centrale Casablanca × BMCI — 2026*
