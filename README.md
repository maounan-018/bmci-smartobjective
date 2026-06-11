# 🎯 ObjectifSMART-AI — BMCI

Application RH d'analyse des objectifs annuels selon la méthode **SMART**
(Spécifique, Mesurable, Atteignable, Réaliste, Temporel) et de leur **alignement
stratégique**, propulsée par une **IA locale** (Ollama). L'application aide
collaborateurs, managers et RH à évaluer la qualité des objectifs **sans jamais
faire sortir les données de l'infrastructure de la banque**.

> Version **3.0** — Frontend **Vue.js (JavaScript)**, backend **Python FastAPI**
> en architecture **MVC + SQLAlchemy ORM**, IA **Ollama** locale, **SSO SAML 2.0**
> (ADFS / Entra ID) et sécurité renforcée. Le backend reste l'unique source de vérité.

---

## 📑 Table des matières

1. [Architecture globale](#1-architecture-globale)
2. [Structure du dépôt](#2-structure-du-dépôt)
3. [Pile technique](#3-pile-technique)
4. [Fonctionnalités](#4-fonctionnalités)
5. [Rôles & isolation des données](#5-rôles--isolation-des-données)
6. [Authentification (SSO / local) & comptes](#6-authentification-sso--local--comptes)
7. [Sécurité & traçabilité](#7-sécurité--traçabilité)
8. [Installation (développement)](#8-installation-développement)
9. [Démarrage](#9-démarrage)
10. [Tests](#10-tests)
11. [Configuration (.env)](#11-configuration-env)
12. [Mise en production (banque)](#12-mise-en-production-banque)
13. [Endpoints principaux](#13-endpoints-principaux)
14. [Dépannage](#14-dépannage)
15. [Équipe](#15-équipe)

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
│   ├── .env                        # Config committée (dev, SANS secret réel)
│   ├── create_user.py              # Outil admin : créer des comptes (rôle inclus)
│   ├── pytest.ini
│   ├── DOCUMENTATION.md             # Documentation technique du backend
│   └── app/
│       ├── main.py                 # Fabrique FastAPI + montage des routers
│       ├── core/                   # config (.env) + security (PBKDF2, tokens, hash)
│       ├── database/               # base, session, init_db, seed (comptes démo)
│       ├── models/                 # Modèles ORM
│       ├── repositories/           # TOUTES les requêtes (aucun SQL ailleurs)
│       ├── services/               # Logique métier (auth, hr_*, manager, ai, …)
│       ├── controllers/            # Routes FastAPI (auth, saml, hr, manager, ai…)
│       ├── schemas/                # Schémas Pydantic (validés)
│       ├── auth/                   # IdentityProvider + providers (local, saml)
│       ├── middlewares/            # request_size (DoS) + security_headers
│       ├── utils/                  # Helpers (score SMART, métadonnées requête)
│       └── tests/                  # pytest (48 tests : sécurité, RBAC, SSO, import)
│
├── frontend/                       # Frontend Vue.js (JavaScript pur)
│   ├── package.json
│   ├── vite.config.js              # Proxy /api -> http://localhost:5001
│   └── src/
│       ├── main.js, App.vue
│       ├── router/, guards/, stores/
│       ├── services/               # apiService, authService (cookies), aiService
│       ├── views/                  # LoginView, *Dashboard, SmartAnalysisView
│       ├── components/, layouts/, utils/
│
├── .gitignore                      # Ignore .env, .env.local, *.db (sauf backend/.env versionné)
├── Modelfile                       # Définition Ollama du modèle smart-qwen8 (REQUIS pour l'IA)
├── requirements.txt                # Dépendances Python (backend)
├── requirements-saml.txt           # Dépendance OPTIONNELLE pour le SSO SAML
├── SSO_SAML.md                     # Guide SSO : simulation → réel → retrait
├── LANCER_APP.bat                  # Démarrage tout-en-un (Windows, autonome)
├── start_app.sh                    # Démarrage tout-en-un (Linux / macOS)
└── README.md
```

---

## 3. Pile technique

### Backend
| Composant | Choix | Rôle |
|---|---|---|
| Framework web | **FastAPI** | Routes, validation, OpenAPI |
| Serveur ASGI | **Uvicorn** | Exécution |
| ORM | **SQLAlchemy 2.0** | Modèles, requêtes, sessions |
| Base de données | **SQLite** (`objectifsmart.db`) | Persistance locale (PostgreSQL en prod) |
| Validation | **Pydantic v2** | Schémas d'entrée bornés |
| SSO | **python3-saml** (optionnel) | SAML 2.0 ADFS / Entra ID |
| IA | **Ollama** (`smart-qwen8`, construit depuis le `Modelfile`) | Modèle local |
| Excel / PDF | **openpyxl** / **reportlab** | Imports & rapports |
| Tests | **pytest** + **httpx** | Tests d'intégration |

### Frontend
| Composant | Choix |
|---|---|
| Framework | **Vue 3** (Composition API) |
| Build | **Vite** |
| Router / État | **vue-router 4** / **Pinia** |
| Graphiques / Icônes | **Chart.js** / **lucide-vue-next** |
| Styles | **Tailwind CSS** |

---

## 4. Fonctionnalités

- **Authentification** : **SSO SAML** (ADFS / Entra ID) ou connexion locale ;
  **aucune inscription publique** (comptes provisionnés par l'admin).
- **Objectifs personnels** : CRUD pour COLLAB, vue d'équipe MANAGER, vue globale HR.
- **Catalogue stratégique** : référentiel des objectifs d'entreprise (HR/MANAGER).
- **Analyse IA SMART** : évaluation des 5 critères + reformulations FR/EN.
- **Alignement stratégique** : score d'alignement (top matches + écarts).
- **Imports Excel** : objectifs collaborateurs & stratégiques (RH), drag & drop.
- **Analyse en lot** (HR) : SMART + alignement de N objectifs en **SSE**.
- **Tableaux de bord analytiques RH** + **exports** Excel / PDF.
- **Audit trail** : journalisation des évènements sensibles (anti-fuite).

---

## 5. Rôles & isolation des données

| Rôle | Périmètre |
|---|---|
| **COLLAB** | Ses propres objectifs uniquement |
| **MANAGER** | Lui-même + son équipe (`manager_id = lui`), hors imports RH |
| **HR** | Vue globale agrégée (imports RH : `data_scope='HR'`) ; accès audit |
| **ADMIN** | Réservé à l'évolution future ; HR fait office d'admin |

> **Isolation stricte** : analyses stockées dans **trois tables séparées**
> (`hr_/manager_/collab_analysis_results`). Une analyse RH n'est jamais visible
> côté Manager et inversement. Le marquage `data_scope` renforce le cloisonnement.

---

## 6. Authentification (SSO / local) & comptes

**Il n'y a pas d'inscription publique** (supprimée : inutile avec le SSO, et
risque d'auto-attribution de rôle). Les comptes sont créés de deux façons :

- **SSO SAML (production)** : au 1ᵉʳ login, le compte est créé automatiquement
  (*JIT provisioning*) avec le rôle déduit des groupes de l'annuaire (Entra/ADFS).
  La connexion locale est alors **coupée automatiquement**.
- **Provisionnement manuel (admin)** via `backend/create_user.py` :
  ```bash
  cd backend
  python create_user.py --email rh@bmci.ma --name "RH BMCI" --role HR --password "MotDePasseFort1"
  python create_user.py --email collab@bmci.ma --role COLLAB --manager rh@bmci.ma
  python create_user.py --list
  ```

**Transport de session** : cookie **HttpOnly + Secure + SameSite** (involable par
XSS) + protection **CSRF** (double-submit). Un en-tête `Authorization: Bearer`
reste accepté pour les clients non-navigateur. Voir [`SSO_SAML.md`](SSO_SAML.md)
pour brancher / simuler / retirer le SSO.

---

## 7. Sécurité & traçabilité

| Mesure | Mise en œuvre |
|---|---|
| **Mots de passe** | PBKDF2-HMAC-SHA256 salé, vérif à temps constant, migration legacy auto |
| **Sessions** | Token aléatoire **hashé en base** (SHA-256), cookie **HttpOnly/Secure/SameSite** |
| **CSRF** | Double-submit (`csrf_token` ↔ `X-CSRF-Token`) sur les mutations par cookie |
| **SSO SAML** | Assertions signées exigées (RSA-SHA256, strict), token **jamais dans l'URL** (code à usage unique) |
| **Inscription** | Supprimée → aucune escalade de rôle ; comptes via SSO/JIT ou `create_user.py` |
| **Login local** | Coupé automatiquement en SSO réel (`LOCAL_AUTH_ENABLED=auto`) |
| **Simulation SSO** | Refusée si `ENV=production` |
| **Validation entrées** | Email validé, longueurs bornées (anti-DoS PBKDF2 / IA) |
| **Anti brute-force** | Blocage 429 par **email ET IP** |
| **CORS** | Origines explicites via `.env`, wildcard `*` interdit (échec démarrage) |
| **En-têtes HTTP** | nosniff, X-Frame-Options DENY, HSTS, Referrer-Policy, CSP `frame-ancestors` |
| **Taille requête** | Middleware 413 au-delà de `MAX_REQUEST_SIZE_MB` |
| **Erreurs** | Messages génériques au client, détail loggué serveur |
| **Audit trail** | Évènements sensibles journalisés, descriptions filtrées, token jamais en clair |

---

## 8. Installation (développement)

### Prérequis
| Outil | Version |
|---|---|
| **Python** | ≥ 3.10 (testé 3.12) |
| **Node.js** | ≥ 18 |
| **Ollama** | dernière version ([installer](https://ollama.com)) |

```bash
# 1) Cloner
git clone https://github.com/LOMPO-ERNEST/bmci-smartobjective.git
cd bmci-smartobjective

# 2) Backend
pip install -r requirements.txt

# 3) Frontend
cd frontend && npm install && cd ..

# 4) Modèle IA local (smart-qwen8, construit depuis le Modelfile)
ollama pull qwen3:8b
ollama create smart-qwen8 -f Modelfile
```

> 💡 `LANCER_APP.bat` (Windows) et `start_app.sh` (Linux/macOS) font ces étapes
> automatiquement si le modèle est absent.

**Configuration** : `backend/.env` est **déjà versionné** (config de dev, **sans
secret réel**). L'application démarre directement après le clone. Pour de vrais
secrets (certificats SSO, etc.) → `backend/.env.local` (ignoré par git, prioritaire).

> 📘 **Guide de déploiement complet** (installation pas à pas sur un **nouveau PC**
> **et** **mise en production** bancaire, avec checklist et dépannage) :
> voir **[`DEPLOIEMENT.md`](DEPLOIEMENT.md)**.

---

## 9. Démarrage

### Option A — Tout-en-un (recommandé)
```bash
# Windows : double-clic ou
LANCER_APP.bat        # vérifie Python/Node, installe les deps, lance tout

# Linux / macOS
./start_app.sh
```

### Option B — Manuel (3 terminaux)
```bash
ollama serve                                                            # 1
cd backend && python -m uvicorn app.main:app --port 5001 --reload       # 2
cd frontend && npm run dev                                              # 3
```

### Accès
- **Application** : http://localhost:3000
- **API Swagger** : http://localhost:5001/docs
- **Health check** : http://localhost:5001/health

### Comptes de démonstration (dev local, créés au démarrage)
| Rôle | Email | Mot de passe |
|---|---|---|
| HR | `hr@bmci.ma` | `REDACTED_DEMO_PWD` |
| Manager | `manager@bmci.ma` | `REDACTED_DEMO_PWD` |
| Collaborateur | `collab@bmci.ma` | `REDACTED_DEMO_PWD` |

> ⚠️ Comptes de **démo uniquement** : désactivés automatiquement en SSO réel,
> à retirer/changer en production (`SEED_DEMO_ACCOUNTS=false`).

---

## 10. Tests

```bash
cd backend && python -m pytest -v        # 48 tests verts
cd frontend && npm run build             # validation build (~1600 modules)
```
Base SQLite **temporaire isolée** (jamais la production). Couverture : sécurité
(PBKDF2, cookies, CSRF, rate-limit, en-têtes), audit, RBAC, auth, SSO SAML, import Excel.

---

## 11. Configuration (`.env`)

| Variable | Rôle |
|---|---|
| `ENV` | `development` (défaut) ou `production` (refuse la simulation SSO) |
| `ALLOWED_ORIGINS` | Origines CORS (obligatoire ; `*` interdit) |
| `SESSION_DURATION_HOURS` / `PBKDF2_ITERATIONS` | Sessions / coût hachage |
| `MAX_LOGIN_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | Anti brute-force |
| `MAX_REQUEST_SIZE_MB` | Limite uploads (défaut 20 Mo) |
| `DATABASE_PATH` | Chemin SQLite |
| `OLLAMA_URL` / `OLLAMA_MODEL` | IA locale (`smart-qwen8`) |
| `AI_MAX_ATTEMPTS` | Réessais IA si réponse vide/non parsable (défaut 2) |
| `AI_RATE_LIMIT_MAX` / `AI_RATE_LIMIT_WINDOW_SECONDS` | Quota d'analyses IA par utilisateur (défaut 10/60 s) |
| `AUTH_PROVIDER` | `local` (défaut) / `saml` |
| `LOCAL_AUTH_ENABLED` | `auto` (défaut) / `true` / `false` — login local |
| `SEED_DEMO_ACCOUNTS` + `SEED_*_PASSWORD` | Comptes démo (dev) |
| `SAML_SIMULATION` | `true` pour tester le SSO sans IdP (dev only) |
| `SAML_SP_*` / `SAML_IDP_*` | Config SSO réel (secrets → `.env.local`) |
| `SAML_ALLOWED_GROUPS` | Filtre d'accès SSO optionnel |

> Détails SSO complets dans [`SSO_SAML.md`](SSO_SAML.md).

---

## 12. Mise en production (banque)

> ⚙️ La mise en production se fait **par-dessus le code**, sans le modifier.
> Étapes recommandées (serveur interne banque) ci-dessous — **guide détaillé pas
> à pas** (build offline, multi-worker, HTTPS, checklist) dans
> **[`DEPLOIEMENT.md`](DEPLOIEMENT.md)** :

1. **Variables d'environnement** dans `backend/.env.local` (jamais committé) :
   ```ini
   ENV=production
   ALLOWED_ORIGINS=https://example.com
   SEED_DEMO_ACCOUNTS=false
   ```
   → en `production` + SSO configuré, **la connexion locale et les comptes démo
   sont automatiquement désactivés**.

2. **Brancher le SSO réel** (valeurs fournies par la DSI) — voir [`SSO_SAML.md`](SSO_SAML.md) :
   ```bash
   pip install -r requirements-saml.txt
   # puis renseigner SAML_SP_* / SAML_IDP_* dans .env.local
   ```
   Transmettre à la DSI l'URL des métadonnées SP : `/api/auth/saml/metadata`.

3. **HTTPS** via un reverse proxy (nginx / IIS) portant le **certificat TLS**
   (interne banque ou Let's Encrypt). Indispensable : les cookies `Secure` et
   l'en-tête HSTS ne sont actifs qu'en HTTPS.

4. **Serveur d'application** : remplacer `uvicorn --reload` par plusieurs workers
   (gunicorn + workers uvicorn sous Linux, ou service Windows).

5. **Base PostgreSQL** recommandée au-delà de SQLite pour la charge concurrente.

6. **Comptes** : provisionner les comptes réels via `create_user.py` (mode local
   de secours) ou laisser le **JIT SSO** créer les comptes au 1ᵉʳ login.

7. **Sauvegardes + supervision** (logs, alertes) et **validation sécu/DSI** (pentest).

---

## 13. Endpoints principaux

| Méthode | Endpoint | Rôle | Description |
|---|---|---|---|
| GET | `/health` | public | Sonde de disponibilité |
| POST | `/api/auth/login` | public | Connexion locale (cookie de session) |
| GET | `/api/auth/saml/status` | public | État du SSO (`enabled`, `simulation`) |
| GET | `/api/auth/saml/login` | public | Démarre le SSO (ADFS / Entra ID) |
| POST | `/api/auth/saml/acs` | public | Réception de l'assertion SAML signée |
| GET | `/api/auth/saml/metadata` | public | Métadonnées SP (pour la DSI) |
| POST | `/api/auth/saml/exchange` | public | Échange du code SSO contre la session |
| POST | `/api/auth/logout` | authentifié | Déconnexion |
| GET | `/api/auth/me` | authentifié | Profil courant |
| GET | `/api/admin/audit-logs` | HR/ADMIN | Journal d'audit |
| GET/POST | `/api/objectives` | authentifié | Lister / créer un objectif |
| GET/POST | `/api/company-objectives` | public / MANAGER-HR | Catalogue stratégique |
| GET | `/api/manager/*` | MANAGER | Dashboard, équipe, analyses, export |
| GET | `/api/collab/analysis-results` | COLLAB | Analyses privées |
| POST | `/api/analyze-smart`, `/api/analyze-alignment` | authentifié | Analyse IA |
| POST | `/api/hr/import-strategy`, `/api/hr/import-objectives` | HR | Imports Excel RH |
| POST | `/api/hr/analyze-batch` | HR | Analyse en lot **SSE** |
| GET | `/api/hr/analytics`, `/api/hr/export-excel`, `/api/hr/export-pdf` | HR | Analytics & rapports |

> Liste complète interactive sur **`/docs`** (Swagger UI).

---

## 14. Dépannage

| Symptôme | Solution |
|---|---|
| Backend refuse de démarrer (`ALLOWED_ORIGINS doit être défini`) | Restaurer `git checkout -- backend/.env` |
| « Ollama n'est pas démarré » | `ollama serve` |
| « Modèle smart-qwen8 non trouvé » | `ollama pull qwen3:8b` puis `ollama create smart-qwen8 -f Modelfile` |
| « Trop d'analyses IA » (HTTP 429) | Quota anti-saturation : patienter ou ajuster `AI_RATE_LIMIT_MAX` |
| Frontend voit 404 sur `/api/*` | Vérifier que le backend tourne sur :5001 (proxy `vite.config.js`) |
| Connexion impossible en local | Vérifier qu'un compte existe (`python create_user.py --list`) |
| Bouton SSO absent | SSO non configuré : voir [`SSO_SAML.md`](SSO_SAML.md) (ou `SAML_SIMULATION=true` en dev) |
| Upload « payload too large » | Augmenter `MAX_REQUEST_SIZE_MB` |

---

## 15. Équipe

**Groupe 03**
- Lompo Bampalou Ernest
- Chaabi Taha
- Jadlaoui Marwen
- Assia Hantoum
- David Danhouegnon

**Encadrement :** Mme Annoukoubi Maha (ECC)
**Entreprise :** BMCI — ABID Chaimaa, ESSAEGH Keltoum

---

*École Centrale Casablanca — Année académique 2024-2025*
