# 🚀 Guide de déploiement — ObjectifSMART-AI BMCI

Ce guide couvre **deux scénarios** :

- **[A. Nouveau PC](#a-déploiement-sur-un-nouveau-pc)** — installer et faire tourner l'app (dev / démo).
- **[B. Production](#b-déploiement-en-production-banque)** — déploiement durci sur serveur interne, **fonctionnel sans Internet**.

> 🟢 **Node.js reste nécessaire** dans les deux cas : c'est lui qui **compile le frontend** (Vite + Tailwind). En production il sert au *build* (`npm run build`) ; l'artefact produit (`frontend/dist/`) est ensuite servi en statique, sans Node ni Internet.

---

## Prérequis communs

| Outil | Version | Vérifier |
|---|---|---|
| **Python** | ≥ 3.10 (testé 3.12) | `python --version` |
| **Node.js** | ≥ 18 | `node --version` |
| **Ollama** | dernière ([ollama.com](https://ollama.com)) | `ollama --version` |

> 💡 Diagnostic automatique à tout moment : **double-clic sur `VERIFIER.bat`** (ou `python verif_projet.py`).
> Il contrôle Python, dépendances backend/frontend, support `sqlite-vec` (RAG), Ollama + ses modèles, fichiers critiques et ports — et indique pour chaque manque **la commande exacte qui répare**.

---

## A. Déploiement sur un nouveau PC

### Option 1 — Tout-en-un (recommandé, le plus simple)

| OS | Commande |
|---|---|
| **Windows** | double-clic sur **`LANCER_APP.bat`** |
| **Linux / macOS** | **`./start_app.sh`** |

Ces scripts font **tout automatiquement** : installation des dépendances Python + npm, **construction du modèle IA `smart-qwen8`** depuis le `Modelfile`, démarrage d'Ollama + backend (`:5001`) + frontend (`:3000`), puis ouverture du navigateur.

### Option 2 — Manuel (4 étapes)

```bash
# 1) Dépendances backend + frontend
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2) Modèles IA locaux (ne quittent jamais la machine) :
#    - smart-qwen8 : analyse SMART (construit depuis le Modelfile, base qwen3:8b).
#    - qwen3:8b    : Coach IA conversationnel (récupéré comme base de smart-qwen8).
#    - bge-m3      : embeddings du RAG / recherche sémantique (à télécharger).
ollama create smart-qwen8 -f Modelfile
ollama pull bge-m3

# 3) Démarrer (3 terminaux)
ollama serve                                                       # terminal 1
cd backend && python -m uvicorn app.main:app --port 5001 --reload  # terminal 2
cd frontend && npm run dev                                         # terminal 3
```

**Accès :** http://localhost:3000 · API Swagger : http://localhost:5001/docs · Santé : http://localhost:5001/health

**Comptes de démonstration** (créés au démarrage, dev uniquement) :

Les comptes démo sont provisionnés quand `SEED_DEMO_ACCOUNTS=true` (défaut en
dev, désactivé automatiquement en SSO réel). Les emails et mots de passe sont
définis dans `backend/.env.local` via les variables `SEED_*_EMAIL` et
`SEED_*_PASSWORD` — jamais commités, à configurer selon la politique de mots
de passe du poste. Récupérer la liste des comptes seedés avec :
```bash
cd backend && python create_user.py --list
```

### À propos du `.env`

`backend/.env` est **déjà versionné** (config de dev, **sans secret réel**) : l'app démarre directement après un clone, **rien à configurer**. Le modèle y est déjà réglé sur `smart-qwen8`.

---

## B. Déploiement en production (banque)

> ⚙️ Principe : la mise en production se fait **par-dessus le code, sans le modifier**. Toute la config prod (et les vrais secrets) va dans **`backend/.env.local`** — ignoré par git, **prioritaire** sur `.env`.

### 1. Build du frontend (offline) — `npm`, via Node

```bash
cd frontend
npm install
npm run build
```

→ génère **`frontend/dist/`** : HTML/CSS/JS **statique et 100 % autonome** — Tailwind est compilé localement et la police Inter est embarquée, **aucun appel à un CDN**. Ce dossier se sert tel quel par **nginx / IIS**. **Aucun accès Internet requis au runtime** (compatible réseau bancaire fermé).

### 2. Config de production — `backend/.env.local`

```ini
ENV=production
ALLOWED_ORIGINS=https://<url-interne-banque>
SEED_DEMO_ACCOUNTS=false
```

→ en `production` **+ SSO configuré**, la **connexion locale et les comptes démo sont coupés automatiquement** (anti porte dérobée).

### 3. Serveur d'application — **multi-worker** (désormais sûr)

L'état sensible (sessions, **anti-brute-force**, **codes SSO**, **quota IA**) est **stocké en base**, donc **partagé entre workers** : on peut scaler sans incohérence. Remplacer `uvicorn --reload` par plusieurs workers :

```bash
# Linux (recommandé) : gunicorn pilotant des workers uvicorn
pip install gunicorn
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:5001

# Multiplateforme (Windows compris) : uvicorn multi-workers
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --workers 4
```

### 4. Base de données

SQLite (`objectifsmart.db`) suffit pour une charge faible. Au-delà → **PostgreSQL** (les tables sont créées automatiquement au démarrage via l'ORM). Prévoir des **sauvegardes** régulières.

### 5. HTTPS — **obligatoire**

Reverse proxy (**nginx / IIS**) portant le **certificat TLS** (interne banque ou Let's Encrypt). Indispensable : les cookies `Secure` et l'en-tête **HSTS** ne s'activent qu'en HTTPS.

### 6. SSO SAML 2.0 (optionnel — ADFS / Entra ID)

```bash
pip install -r requirements-saml.txt
# puis renseigner SAML_SP_* / SAML_IDP_* dans backend/.env.local
```

Transmettre à la DSI l'URL des métadonnées SP : **`/api/auth/saml/metadata`**. Guide complet : [`SSO_SAML.md`](SSO_SAML.md).

### 7. IA locale (Ollama)

Sur le serveur : `ollama create smart-qwen8 -f Modelfile` **et** `ollama pull bge-m3` (embeddings du RAG / Coach). Tout tourne **en local, rien ne sort de l'infra**. Ajuster l'anti-saturation via `AI_RATE_LIMIT_MAX` / `AI_RATE_LIMIT_WINDOW_SECONDS`.

### 8. Comptes réels

Provisionner via `python backend/create_user.py --email … --role … --password …`, **ou** laisser le **JIT SSO** créer les comptes au 1ᵉʳ login (rôle déduit des groupes annuaire).

---

## Variables `.env` clés

| Variable | Rôle | Défaut |
|---|---|---|
| `ENV` | `development` / `production` | `development` |
| `ALLOWED_ORIGINS` | Origines CORS (**obligatoire**, `*` interdit) | — |
| `OLLAMA_MODEL` | Modèle d'analyse SMART (doit exister localement) | `smart-qwen8` |
| `OLLAMA_CHAT_MODEL` | Modèle du Coach IA conversationnel | `qwen3:8b` |
| `OLLAMA_EMBED_MODEL` | Modèle d'embeddings (RAG / recherche sémantique) | `bge-m3` |
| `AI_MAX_ATTEMPTS` | Essais d'appel IA (réessai si réponse vide `{}`) | `2` |
| `AI_RATE_LIMIT_MAX` / `AI_RATE_LIMIT_WINDOW_SECONDS` | Quota d'analyses IA par utilisateur (anti-saturation) | `10` / `60` |
| `SESSION_DURATION_HOURS` / `PBKDF2_ITERATIONS` | Sessions / coût de hachage | `24` / `200000` |
| `MAX_LOGIN_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | Anti-brute-force (état en base) | `5` / `15` |
| `SEED_DEMO_ACCOUNTS` | Comptes démo (à mettre `false` en prod) | `true` |
| `AUTH_PROVIDER` / `LOCAL_AUTH_ENABLED` | Mode d'authentification | `local` / `auto` |

---

## ✅ Checklist de mise en production

- [ ] `cd frontend && npm run build` → `dist/` servi par **nginx / IIS**
- [ ] `backend/.env.local` : `ENV=production`, `ALLOWED_ORIGINS=https://…`, `SEED_DEMO_ACCOUNTS=false`
- [ ] **HTTPS** actif (reverse proxy + certificat TLS)
- [ ] Backend lancé en **multi-worker** (gunicorn/uvicorn `-w 4`)
- [ ] **Ollama** + ses **3 modèles** : `smart-qwen8` (`ollama create … -f Modelfile`), `qwen3:8b` (base, auto) et **`bge-m3`** (`ollama pull bge-m3`, pour le RAG / Coach)
- [ ] (option) **SSO SAML** configuré + métadonnées transmises à la DSI
- [ ] **PostgreSQL** si charge concurrente, **sauvegardes** BDD planifiées
- [ ] Supervision (logs, alertes) + validation sécurité / DSI

---

## 🔧 Dépannage rapide

| Symptôme | Solution |
|---|---|
| Backend refuse de démarrer (`ALLOWED_ORIGINS doit être défini`) | Vérifier `backend/.env` (ou restaurer : `git checkout -- backend/.env`) |
| « Ollama n'est pas démarré » (HTTP 503) | `ollama serve` |
| Modèle introuvable (analyse vide) | `ollama create smart-qwen8 -f Modelfile` (doit matcher `OLLAMA_MODEL`) |
| HTTP 429 sur une analyse | Quota IA atteint — attendre, ou augmenter `AI_RATE_LIMIT_MAX` |
| Front 404 sur `/api/*` (dev) | Le backend doit tourner sur `:5001` (proxy `vite.config.js`) |
| Styles cassés en prod | Servir `frontend/dist/` (issu de `npm run build`), pas `index.html` brut |
| Connexion locale impossible | Vérifier qu'un compte existe : `python backend/create_user.py --list` |
| RAG / base de connaissances / Coach IA sans contexte | Modèle d'embeddings manquant : `ollama pull bge-m3` |
