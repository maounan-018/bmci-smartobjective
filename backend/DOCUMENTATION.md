# Documentation technique du Backend — ObjectifSMART-AI (BMCI)

> Application RH d'analyse des objectifs annuels selon la méthode **SMART** et de
> leur **alignement stratégique**, propulsée par une IA locale (**Ollama**), sans
> jamais faire sortir les données de l'infrastructure de la banque.
>
> Backend **Python / FastAPI** organisé en **architecture en couches (MVC + services
> + repositories)**, persistance **SQLAlchemy ORM** sur **SQLite**.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Pile technique](#2-pile-technique)
3. [Architecture en couches](#3-architecture-en-couches)
4. [Arborescence du projet](#4-arborescence-du-projet)
5. [Cycle de vie d'une requête](#5-cycle-de-vie-dune-requête)
6. [Couche `core` — configuration & sécurité](#6-couche-core--configuration--sécurité)
7. [Couche `database` — connexion ORM](#7-couche-database--connexion-orm)
8. [Couche `models` — modèles ORM](#8-couche-models--modèles-orm)
9. [Couche `repositories` — accès aux données](#9-couche-repositories--accès-aux-données)
10. [Couche `services` — logique métier](#10-couche-services--logique-métier)
11. [Couche `controllers` — routes API](#11-couche-controllers--routes-api)
12. [Couche `auth` — fournisseurs d'identité](#12-couche-auth--fournisseurs-didentité)
13. [Couche `middlewares`](#13-couche-middlewares)
14. [Couche `schemas` — contrats Pydantic](#14-couche-schemas--contrats-pydantic)
15. [Couche `utils`](#15-couche-utils)
16. [Sécurité & traçabilité](#16-sécurité--traçabilité)
17. [Isolation stricte des données par rôle](#17-isolation-stricte-des-données-par-rôle)
18. [Module IA (Ollama)](#18-module-ia-ollama)
19. [Pipeline d'import Excel](#19-pipeline-dimport-excel)
20. [Exports Excel / PDF](#20-exports-excel--pdf)
21. [Référence des endpoints](#21-référence-des-endpoints)
22. [Tests](#22-tests)
23. [Configuration (.env)](#23-configuration-env)
24. [Démarrage](#24-démarrage)
25. [Évolutions prévues](#25-évolutions-prévues)

---

## 1. Vue d'ensemble

Le backend est la **source de vérité unique** pour la sécurité et les données. Le
frontend (Vue.js) ne fait qu'afficher : toute décision d'autorisation, tout calcul
d'analyse et toute persistance sont assurés côté serveur.

Fonctionnalités principales :

- **Authentification locale** (sessions à token) + **SSO SAML 2.0** (ADFS / Entra ID).
- **Gestion des utilisateurs** : rôles `COLLAB`, `MANAGER`, `HR` (et `ADMIN` réservé au futur).
- **Objectifs** : saisie, import Excel (objectifs collaborateurs et objectifs stratégiques).
- **Analyse IA** : caractère **SMART** (Spécifique, Mesurable, Atteignable, Réaliste, Temporel)
  et **alignement stratégique**, avec génération de **recommandations** et de **reformulations**.
- **Tableaux de bord RH** : statistiques, comparaisons par entité/manager/période, points bloquants.
- **Exports** : rapports **Excel** (multi-feuilles) et **PDF**.
- **Audit trail** : journalisation filtrée des évènements sensibles.

---

## 2. Pile technique

| Composant | Choix | Rôle |
|---|---|---|
| Framework web | **FastAPI** | Routes, validation, injection de dépendances, OpenAPI |
| Serveur ASGI | **Uvicorn** | Exécution de l'application |
| ORM | **SQLAlchemy 2.0** | Modèles, requêtes, sessions |
| Base de données | **SQLite** (`objectifsmart.db`) | Persistance locale (fichier) |
| Validation | **Pydantic v2** | Schémas d'entrée/sortie |
| IA | **Ollama** (`smart-qwen8`) | Modèle local d'analyse |
| Excel | **openpyxl** | Lecture/écriture de classeurs |
| PDF | **reportlab** | Génération de rapports PDF |
| HTTP client | **requests** | Appels à Ollama |
| Tests | **pytest** + **httpx** | Tests unitaires & d'intégration |

> Toutes les versions sont **épinglées** dans `requirements.txt` (revues via Dependabot).

---

## 3. Architecture en couches

Le backend suit une séparation stricte des responsabilités. Chaque couche ne parle
qu'à la couche immédiatement inférieure :

```
        HTTP (Frontend Vue.js)
               │
       ┌───────▼─────────┐
       │   controllers   │  Routes FastAPI (fines). Aucune logique métier lourde.
       └───────┬─────────┘
       ┌───────▼─────────┐
       │    services     │  Logique métier : règles, orchestration, IA, exports.
       └───────┬─────────┘
       ┌───────▼─────────┐
       │  repositories   │  TOUTES les requêtes SQLAlchemy. Aucun SQL ailleurs.
       └───────┬─────────┘
       ┌───────▼─────────┐
       │     models      │  Modèles ORM (tables, colonnes, relations).
       └───────┬─────────┘
       ┌───────▼─────────┐
       │    database     │  Engine + sessions SQLAlchemy (SQLite).
       └─────────────────┘

Couches transverses : core (config + sécurité), schemas (Pydantic),
auth (fournisseurs d'identité), middlewares, utils.
```

**Règles d'or :**

- Un **controller** ne contient **jamais** de SQL ni de logique métier ; il appelle un service.
- Un **service** ne fait **jamais** de SQL directement ; il appelle un repository.
- Un **repository** est le **seul** endroit où vivent les requêtes (ORM ou `text()`).
- Un **model** ne contient que la structure des données (et de petits helpers comme `to_dict`).
- Un **schema** ne contient aucune logique métier (validation/typage uniquement).

---

## 4. Arborescence du projet

```
backend/
├── pytest.ini
└── app/
    ├── main.py                    # Fabrique FastAPI + montage routers + init_db (lifespan)
    │
    ├── core/
    │   ├── config.py              # Chargement .env + objet `settings`
    │   └── security.py            # PBKDF2, vérif/migration hash, tokens, anti brute-force
    │
    ├── database/
    │   ├── base.py                # Base déclarative (DeclarativeBase)
    │   ├── session.py             # engine + SessionLocal + get_db + db_session
    │   └── init_db.py             # create_all (idempotent)
    │
    ├── models/                    # Modèles SQLAlchemy ORM
    │   ├── user.py                # User
    │   ├── session.py             # Session (token de session)
    │   ├── objective.py           # Objective
    │   ├── company_objective.py   # CompanyObjective
    │   ├── analysis_result.py     # HRAnalysisResult / ManagerAnalysisResult / CollabAnalysisResult
    │   ├── audit_log.py           # AuditLog + AuditEventType
    │   ├── hr_import.py           # HRImport
    │   └── audit_log_model.py     # Shim de compatibilité (déprécié)
    │
    ├── repositories/              # Accès aux données (SQLAlchemy)
    │   ├── user_repository.py
    │   ├── session_repository.py
    │   ├── objective_repository.py
    │   ├── company_objective_repository.py
    │   ├── analysis_repository.py
    │   ├── audit_repository.py
    │   └── hr_import_repository.py
    │
    ├── services/                  # Logique métier
    │   ├── auth_service.py
    │   ├── user_service.py
    │   ├── objective_service.py
    │   ├── manager_service.py
    │   ├── hr_service.py
    │   ├── ai_service.py
    │   ├── audit_service.py
    │   ├── permission_service.py
    │   ├── excel_import_service.py
    │   └── export_service.py
    │
    ├── controllers/               # Routes FastAPI (un router par domaine)
    │   ├── auth_controller.py     # + dépendance get_current_user
    │   ├── admin_controller.py
    │   ├── objective_controller.py
    │   ├── manager_controller.py
    │   ├── hr_controller.py
    │   └── ai_controller.py
    │
    ├── auth/                      # Authentification (abstraction d'identité)
    │   ├── identity_provider.py   # Contrat IdentityProvider + fabrique + mapping groupes
    │   └── providers/
    │       ├── local_provider.py  # Auth via base locale
    │       └── saml_provider.py   # SSO SAML 2.0 (ADFS / Entra ID)
    │
    ├── middlewares/
    │   └── request_size.py        # Limite de taille des requêtes (anti-DoS)
    │
    ├── schemas/                   # Contrats Pydantic
    │   ├── auth_schema.py
    │   ├── user_schema.py
    │   ├── objective_schema.py
    │   ├── analysis_schema.py
    │   ├── hr_schema.py
    │   └── business_schema.py     # Shim de compatibilité (réexporte les schémas)
    │
    ├── utils/
    │   └── helpers.py             # Conversions sûres, calcul SMART, métadonnées requête
    └── tests/                     # Tests sécurité / traçabilité / RBAC / import
        ├── conftest.py            # Base temporaire isolée (ORM) + fixtures
        ├── test_security.py
        ├── test_audit.py
        ├── test_permissions.py
        ├── test_auth_endpoints.py
        └── test_hr_import.py
```

---

## 5. Cycle de vie d'une requête

Exemple : `GET /api/objectives` (lister les objectifs de l'utilisateur connecté).

1. **Uvicorn → FastAPI** reçoit la requête.
2. Le **middleware** `LimitRequestSizeMiddleware` vérifie `Content-Length` (rejette > 20 Mo).
3. Le **middleware CORS** valide l'origine.
4. Le router `objective_controller` mappe l'URL vers `list_objectives`.
5. La **dépendance** `get_current_user` (dans `auth_controller`) :
   - lit le header `Authorization: Bearer <token>` ;
   - appelle `auth_service.resolve_session_user(token)` qui interroge
     `user_repository.get_by_valid_session` (jointure `users`↔`sessions`, expiration vérifiée) ;
   - en cas d'échec, journalise un évènement d'audit et lève **401**.
6. Le **controller** appelle `objective_service.list_objectives(current_user)`.
7. Le **service** :
   - calcule le périmètre accessible via `permission_service.get_accessible_user_ids` (RBAC) ;
   - ouvre une session via `db_session()` et appelle `objective_repository.list_by_user_ids` ;
   - désérialise les analyses JSON et enrichit chaque objectif (nom/email du propriétaire).
8. Le **repository** exécute la requête SQLAlchemy et renvoie des objets ORM.
9. La réponse (dict JSON) remonte controller → FastAPI → client.

```
Client → [Middlewares] → Controller → Service → Repository → ORM/DB
                                 │
                          permission_service (RBAC)
                          audit_service (traçabilité)
```

---

## 6. Couche `core` — configuration & sécurité

### `core/config.py`

- `load_dotenv()` : charge un fichier `.env` simple (clé=valeur) sans dépendance externe.
  N'écrase jamais une variable déjà présente dans l'environnement réel.
- Classe `Settings` : expose toute la configuration via l'objet **`settings`** (instance unique).
  C'est **l'unique source** de configuration ; aucun secret n'est codé en dur ailleurs.
- **Garde-fou CORS** : si `ALLOWED_ORIGINS` est vide ou `"*"`, le démarrage **échoue**
  (un wildcard combiné à `allow_credentials=True` ouvrirait une faille CSRF).

### `core/security.py`

Primitives cryptographiques (bibliothèque standard uniquement) :

- `hash_password()` — **PBKDF2-HMAC-SHA256** salé (sel aléatoire de 16 octets, coût configurable).
  Format stocké : `pbkdf2_sha256$<iterations>$<sel_hex>$<hash_hex>`.
- `verify_password()` — comparaison **à temps constant** (`hmac.compare_digest`).
  Supporte aussi l'**ancien format SHA-256 simple** (legacy) pour migration transparente.
- `needs_rehash()` — indique si un hash legacy doit être migré (fait à la connexion).
- `generate_token()` — token de session cryptographiquement sûr (`secrets.token_urlsafe(32)`).
- **Anti brute-force** (`services/throttle_service.py`, état **EN BASE** — table
  `login_attempts`) : `is_login_allowed`, `record_failed_login`, `reset_login_attempts` —
  blocage après `MAX_LOGIN_ATTEMPTS` échecs pendant `LOGIN_LOCKOUT_MINUTES`. Le compteur
  est partagé entre workers et survit au redémarrage (l'ancien dictionnaire en mémoire
  ne tenait pas en multi-worker).

---

## 7. Couche `database` — connexion ORM

### `database/base.py`

```python
class Base(DeclarativeBase):
    ...
```

Classe de base déclarative dont héritent tous les modèles. Isolée dans son propre
fichier pour éviter les imports circulaires (`models → base`, jamais `models → session`).

### `database/session.py`

- **`engine`** : `create_engine("sqlite:///<DB_PATH>", connect_args={"check_same_thread": False})`.
- **`SessionLocal`** : fabrique de sessions (`expire_on_commit=False` pour pouvoir lire les
  attributs après commit et renvoyer des dict aux controllers).
- **`get_db()`** : dépendance FastAPI (`yield`) — une session par requête, fermée à la fin.
- **`db_session()`** : gestionnaire de contexte transactionnel pour les services
  (commit si succès, rollback si exception, close systématique).

```python
with db_session() as db:
    user_repository.create(db, ...)
    # commit automatique en sortie de bloc
```

### `database/init_db.py`

- **`init_db()`** : `Base.metadata.create_all(engine)` — **idempotent** (ne recrée jamais
  une table existante, donc préserve les données de `objectifsmart.db`). Importer le paquet
  `app.models` garantit l'enregistrement de toutes les tables avant `create_all`.
- Appelé au **démarrage** de l'app (`main.lifespan`) et par la suite de tests.

---

## 8. Couche `models` — modèles ORM

> **Fidélité au schéma réel** : les identifiants sont des **chaînes** (`user-xxxx`,
> `obj-xxxx`, `STRAT-xxxx`…) et les dates sont stockées en **TEXT** (ISO /
> `CURRENT_TIMESTAMP`), conformément à la base existante. Les analyses SMART/alignement
> sont stockées en **JSON sérialisé (TEXT)** et désérialisées dans la couche service.

### `User` (table `users`)

| Colonne | Type | Notes |
|---|---|---|
| `id` | String, PK | ex. `user-ab12` |
| `email` | String, unique, index | |
| `password_hash` | String | jamais exposé en API |
| `name` | String | |
| `role` | String | `COLLAB` / `MANAGER` / `HR` (contrainte CHECK) |
| `manager_id` | String, FK `users.id` | auto-référence hiérarchique |
| `team`, `entity` | String | |
| `created_at` | String | `CURRENT_TIMESTAMP` |

Relations : `manager` / `subordinates` (auto-référence), `objectives`, `sessions`.
Méthode `to_dict()` — projection **sans** le hash.

### `Session` (table `sessions`)

`token` (PK), `user_id` (FK `users.id`, `ON DELETE CASCADE`), `expires_at`, `created_at`.
Le token **n'est jamais** journalisé en clair (cf. `session_ref`).

### `Objective` (table `objectives`)

Texte de l'objectif (`title`, `description`, `context`), état (`status`, `progress`),
analyses (`smart_analysis`, `alignment_analysis` en JSON TEXT), traçabilité d'analyse
(`analyzed_by_role`, `analyzed_by_user_id`) et **métadonnées d'isolation**
(`data_scope`, `entity`, `manager_name`, `period`, `import_batch_id`). FK `user_id`.

### `CompanyObjective` (table `company_objectives`)

Catalogue stratégique : `title`, `description`, `department`, `priority`, `weight`,
`created_by`, `import_batch_id`. Sert de référentiel à l'analyse d'alignement.

### Résultats d'analyse — **trois tables séparées** (`analysis_result.py`)

L'isolation stricte par rôle impose des tables **physiquement distinctes** ; un mixin
`AnalysisResultMixin` factorise le socle commun (sous-scores `s/m/a/r/t_score`,
`smart_score`, `alignment_score`, `issues_count`, `top_issue`, `analyzed_at`, etc.) :

- **`HRAnalysisResult`** → `hr_analysis_results`
- **`ManagerAnalysisResult`** → `manager_analysis_results` (+ `manager_id`)
- **`CollabAnalysisResult`** → `collab_analysis_results` (+ `user_id`, `objective_description`,
  `rewrite_fr`, `rewrite_en`)

`AnalysisResult` est un **alias** de `HRAnalysisResult` pour les usages génériques.

### `AuditLog` (table `audit_logs`)

`id` (INTEGER auto-incrément), acteur (`user_id`, `username`, `role`), évènement
(`event_type`, `event_status`), contexte (`ip_address`, `user_agent`, `endpoint`,
`http_method`), `description` (filtrée), `session_ref` (hash court non réversible),
`created_at`. L'énumération **`AuditEventType`** liste les évènements traçables
(`LOGIN_SUCCESS`, `LOGIN_FAILED`, `ACCESS_DENIED`, `SESSION_EXPIRED`, …).

### `HRImport` (table `hr_imports`)

Journal des imports Excel RH : `import_type` (`objectives` | `strategy`), `filename`,
`records_count`, `user_id`, `created_at`.

---

## 9. Couche `repositories` — accès aux données

Chaque repository **encapsule toutes les requêtes** d'un domaine. Les fonctions reçoivent
une session ORM (`db: Session`) ouverte par le service appelant et **ne committent pas
elles-mêmes** (le service gère la transaction).

| Repository | Responsabilité |
|---|---|
| `user_repository` | Lecture par id/email, **validation de session** (jointure users↔sessions), création, migration de hash, périmètre d'équipe (`get_team_ids`, `get_all_ids`), `is_manager`. |
| `session_repository` | Création / purge des sessions par utilisateur. |
| `objective_repository` | CRUD objectifs, filtres de périmètre (exclusion HR pour la vue Manager), upsert (`merge`), agrégations d'équipe (compte, analyses, répartition d'avancement), sélection pour analyse en lot. |
| `company_objective_repository` | Catalogue stratégique : liste complète, projection `{id,title,description}` pour l'IA, création/upsert. |
| `analysis_repository` | CRUD des **3 tables d'analyse** + **toutes les requêtes de reporting RH** (analytics, exports). |
| `audit_repository` | Insertion et lecture paginée des logs d'audit. |
| `hr_import_repository` | Création et historique des imports RH. |

### ORM vs `text()`

- Le **CRUD** et les requêtes simples utilisent l'**ORM** (`select()`, `db.scalars(...)`,
  `db.merge(...)`).
- Les **requêtes analytiques complexes** (jointures multiples, `COALESCE`, agrégats,
  `strftime`, `UNION`, `CASE`) sont exprimées via **`text()`** exécuté **par la session
  SQLAlchemy**, à l'intérieur du repository. C'est un patron de *reporting* légitime : tout
  l'accès aux données reste centralisé dans la couche repository, et le comportement SQLite
  d'origine est reproduit fidèlement.

> **Sécurité des requêtes `text()`** : tous les filtres dynamiques passent par des
> **paramètres nommés** (jamais de concaténation de valeurs utilisateur). Les rares noms
> de colonnes dynamiques (ex. critère SMART) sont validés contre une **liste blanche**.

---

## 10. Couche `services` — logique métier

| Service | Rôle principal |
|---|---|
| **`auth_service`** | `register` (toujours COLLAB, anti-escalade), `login` (rate limiting → fournisseur d'identité → migration de hash → session unique → audit), `logout`, `resolve_session_user`. |
| **`user_service`** | Liste publique des managers (id/name/team, sans email), membres d'équipe selon le rôle. |
| **`objective_service`** | CRUD des objectifs (avec RBAC), catalogue stratégique (création + batch), statistiques d'équipe génériques. |
| **`manager_service`** | Objectifs d'équipe (hors imports RH), stats, analyses privées Manager & Collaborateur, analyse SMART d'un objectif d'équipe ou personnel, export Excel/PDF. |
| **`hr_service`** | Analyse personnelle RH, imports Excel (objectifs & stratégie), analyse en lot **SSE**, tableaux de bord analytiques, liste détaillée, exports Excel/PDF, historique des imports. |
| **`ai_service`** | Appels au modèle **Ollama**, heuristiques de cohérence, analyses SMART & alignement réutilisables. *(Pur : aucun accès base.)* |
| **`excel_import_service`** | Détection intelligente des colonnes, extraction/déduplication, analyse en lot, génération d'un Excel enrichi, **orchestration import + stockage par rôle**. |
| **`export_service`** | Génération de documents **Excel** et **PDF** (rapports Manager et RH). *(Pur : reçoit des données déjà extraites.)* |
| **`audit_service`** | Écriture/lecture des logs (via `audit_repository`), **filtrage anti-fuite** des descriptions, hachage de session. Ne lève **jamais** à l'écriture. |
| **`permission_service`** | **RBAC** : `require_role`, `require_admin`, `require_own_resource`, `check_collab_access`, `check_manager_access`, périmètre de données (`get_accessible_user_ids`). |

**Points clés de logique métier :**

- **Anti-escalade de rôle** : `register` force toujours `COLLAB` (le rôle envoyé par le
  client est ignoré) et exige un manager existant.
- **Migration transparente des mots de passe** : à la connexion, un hash legacy SHA-256 est
  ré-haché en PBKDF2 sans intervention de l'utilisateur.
- **Score SMART** : pourcentage calculé à partir des 5 booléens `S/M/A/R/T`
  (`(S+M+A+R+T)/5 × 100`).
- **Génération de comptes à l'import** (F10) : chaque collaborateur créé reçoit un mot de
  passe **aléatoire fort par compte** (`secrets.token_urlsafe(16)`), **jamais** un seed
  partagé ; les credentials temporaires sont renvoyés pour transmission individuelle.

---

## 11. Couche `controllers` — routes API

Les controllers sont **fins** : ils déclarent un `APIRouter`, injectent
`get_current_user` quand l'authentification est requise, et délèguent au service.

| Controller | Préfixe | Domaine |
|---|---|---|
| `auth_controller` | `/api` | `/auth/*` + dépendance `get_current_user` |
| `admin_controller` | `/api/admin` | `/audit-logs` |
| `objective_controller` | `/api` | `/objectives`, `/company-objectives`, `/team/*` |
| `manager_controller` | `/api` | `/manager/*`, `/collab/analysis-results` |
| `hr_controller` | `/api/hr` | analyses, imports, analytics, exports |
| `ai_controller` | `/api` | `/analyze-*`, `/import-excel-*`, `/scan-excel` |
| `saml_controller` | `/api/auth/saml` | `/status`, `/metadata`, `/login`, `/acs` (SSO SAML) |

La dépendance **`get_current_user`** (définie une fois dans `auth_controller`) est réutilisée
par tous les autres controllers : c'est le point d'entrée unique de l'authentification.

---

## 12. Couche `auth` — fournisseurs d'identité

Le mécanisme d'authentification est **abstrait** derrière un contrat, pour pouvoir basculer
de l'auth locale vers l'IAM bancaire **sans toucher aux services/controllers**.

- **`identity_provider.py`** : classe abstraite `IdentityProvider`
  (`authenticate`, `get_user_groups`), table `BANK_GROUP_TO_ROLE`,
  fonction `map_groups_to_role` (priorité ADMIN > HR > MANAGER > COLLAB), et **fabrique**
  `get_identity_provider()` qui retourne le provider local (le SSO SAML suit un flux dédié).
- **`providers/local_provider.py`** : `LocalDatabaseProvider` — vérifie l'email + le mot de
  passe contre la base locale via `user_repository` et `verify_password`. Retourne un profil
  normalisé `{external_id, email, display_name, groups}`.
- **`providers/saml_provider.py`** : `SamlProvider` — encapsule python3-saml (assertion
  signée). L'authentification fédérée passe par `controllers/saml_controller.py` (cf. `SSO_SAML.md`).

Profil normalisé renvoyé par tout fournisseur :

```json
{ "external_id": "user-ab12", "email": "...", "display_name": "...", "groups": ["MANAGER"] }
```

---

## 13. Couche `middlewares`

- **`LimitRequestSizeMiddleware`** : première ligne de défense **anti-DoS par upload massif**.
  Vérifie le header `Content-Length` **avant** toute lecture du corps ; renvoie **413** si la
  taille dépasse `MAX_REQUEST_SIZE_MB` (20 Mo par défaut). Appliqué **avant** le CORS.
- **CORS** (configuré dans `main.py`) : origines restreintes via `.env`, jamais `"*"`.

---

## 14. Couche `schemas` — contrats Pydantic

Validation et typage des entrées/sorties, **sans logique métier** :

- `auth_schema` : `LoginRequest`, `UserPublic` (l'inscription publique a été supprimée — comptes via SSO/JIT ou seed).
- `user_schema` : `UserPublic`, `ManagerPublic` (sans email).
- `objective_schema` : `ObjectiveCreate`, `ObjectiveUpdate`, `CompanyObjectiveCreate`.
- `analysis_schema` : `SmartRequest`, `AlignmentRequest`, `ManagerPersonalAnalysisRequest`.
- `hr_schema` : `HRPersonalAnalysisRequest`.
- `business_schema` : **shim** qui réexporte les schémas ci-dessus (compatibilité).

---

## 15. Couche `utils`

`helpers.py` — fonctions pures, sans état ni accès base :

- `safe_int` / `safe_float` : conversions tolérantes.
- `calculate_smart_total` / `is_smart_valid` : total des sous-scores SMART et validité (≥ 4).
- `request_meta` : extrait `(ip, user_agent, endpoint, method)` d'une requête (pour l'audit).

---

## 16. Sécurité & traçabilité

| Mesure | Mise en œuvre |
|---|---|
| **Mots de passe** | PBKDF2-HMAC-SHA256 salé ; vérification à temps constant ; migration auto depuis SHA-256 legacy. |
| **Sessions** | Tokens aléatoires (`secrets`), expiration configurable, session unique par utilisateur (les anciennes sont purgées à la connexion). |
| **Anti brute-force** | Blocage temporaire après N échecs (HTTP **429**). |
| **CORS** | Origines explicites via `.env` ; wildcard interdit (anti-CSRF). |
| **Taille de requête** | Rejet **413** au-delà de la limite (anti-DoS upload). |
| **Autorisation (RBAC)** | Centralisée dans `permission_service` ; le backend est seul juge. |
| **Audit trail** | Évènements sensibles journalisés ; **descriptions filtrées** (aucun mot de passe/token/secret) ; tokens jamais en clair (`session_ref` = hash court). Consultation réservée HR/ADMIN. |
| **Anti-escalade** | L'inscription publique ne crée que des comptes COLLAB. |
| **Secrets** | Uniquement via `.env` (jamais en dur). `.env.local` et `*.db` exclus de git. |

**Filtrage anti-fuite de l'audit** : toute description contenant un mot-clé sensible
(`password`, `token`, `secret`, `otp`, …) est remplacée par
`[DESCRIPTION FILTRÉE — contenu potentiellement sensible]`.

---

## 17. Isolation stricte des données par rôle

L'application garantit qu'**un rôle ne voit jamais les données d'un autre** :

- **Périmètre de données** (`get_accessible_user_ids`) :
  - `COLLAB` → uniquement lui-même ;
  - `MANAGER` → uniquement son équipe (`manager_id = lui`) ;
  - `HR` → vue globale (analytics agrégés).
- **Tables d'analyse séparées** : `hr_analysis_results`, `manager_analysis_results`,
  `collab_analysis_results` — aucune fuite croisée possible.
- **Marquage `data_scope`** sur les objectifs : les imports/analyses RH sont marqués `'HR'`
  (et `import_batch_id LIKE 'obj-%'`). La **vue Manager exclut** explicitement ces objectifs,
  et **l'analytics RH ne lit que** ce périmètre. Manager et RH sont ainsi cloisonnés.

---

## 18. Module IA (Ollama)

`ai_service` centralise toute l'interaction avec le modèle local **Ollama** :

- **`call_ollama(prompt, system)`** : appel HTTP (`format=json`, `stream=false`), URL et nom de
  modèle issus de la config. Gestion d'erreurs explicite : **503** (Ollama éteint),
  **504** (timeout), **500** (réponse invalide).
- **`extract_json_from_text`** : extraction tolérante du JSON (markdown, bruit, accolades).
- **Heuristiques de cohérence** (`has_measure`, `has_time`, `enforce_consistency`) : corrigent
  les incohérences du modèle — par ex. un critère **M** affirmé sans indicateur chiffré, ou
  **T** sans échéance, sont remis à `false` ; `overall` est recalculé (`S∧M∧A∧R∧T`).
- **`analyze_smart_internal`** : renvoie `{S,M,A,R,T, overall, confidence, issues[], rewrite_fr, rewrite_en}`.
- **`analyze_alignment_internal`** : renvoie `{alignment_score, top_matches[], gaps[]}`
  (au plus 3 correspondances) ; tombe en valeurs neutres si l'IA est indisponible.

> Aucune donnée ne quitte l'infrastructure : le modèle tourne **en local**.

---

## 19. Pipeline d'import Excel

`excel_import_service` implémente un import **tolérant aux fichiers désordonnés** :

1. **Détection des colonnes** (`ExcelColumnDetector`) : score chaque colonne comme
   « objectif » ou « description » à partir de mots-clés (FR/EN, sans accents), de la
   similarité (`difflib`) et de la nature des valeurs (longueur moyenne, verbes d'action).
2. **Scan** (`scan_excel_file`) : explore toutes les feuilles, retient la meilleure colonne.
3. **Extraction** (`extract_objectives_from_excel`) : nettoyage, déduplication, conservation
   de l'origine (feuille/ligne) pour réinjecter les résultats.
4. **Analyse en lot** (`analyze_objectives_batch`) : SMART + alignement pour chaque objectif.
5. **Stockage par rôle** (`run_import_analyze`) : les résultats sont rangés dans la table
   privée correspondant au rôle de l'utilisateur (manager/hr/collab).
6. **Excel enrichi** (`run_import_export` / `create_result_excel`) : reprend la structure
   d'origine et ajoute les colonnes d'analyse, avec code couleur (bon/moyen/faible).

Côté RH, `hr_service.import_objectives` / `import_strategy` gèrent en plus la **création des
comptes manquants** (mot de passe temporaire fort) et la **journalisation** de l'import.

---

## 20. Exports Excel / PDF

`export_service` (pur — reçoit des données déjà extraites par les services) génère :

- **Rapport Manager** : `generate_manager_excel` (3 feuilles : objectifs équipe, analyses
  perso, résumé) et `generate_manager_pdf` (synthèse + tableaux).
- **Rapport RH** : `generate_hr_excel` (4 feuilles : objectifs détaillés, stats par entité,
  stats par manager, points bloquants SMART) et `generate_hr_pdf` (synthèse + détail).

Les fichiers sont renvoyés en **`StreamingResponse`** avec un en-tête
`Content-Disposition: attachment`. La disponibilité d'`openpyxl`/`reportlab` est détectée ;
en leur absence, une **500** explicite est renvoyée.

---

## 21. Référence des endpoints

| Méthode | Endpoint | Rôle requis | Description |
|---|---|---|---|
| GET | `/health` | public | Sonde de disponibilité |
| POST | `/api/auth/login` | public | Connexion locale (token de session) |
| GET | `/api/auth/saml/login` | public | Démarre le SSO (ADFS / Entra ID) |
| POST | `/api/auth/saml/acs` | public | Réception de l'assertion SAML |
| POST | `/api/auth/logout` | authentifié | Déconnexion |
| GET | `/api/auth/me` | authentifié | Profil courant |
| GET | `/api/admin/audit-logs` | HR/ADMIN | Journal d'audit |
| GET/POST | `/api/objectives` | authentifié | Lister / créer un objectif |
| GET/PUT/DELETE | `/api/objectives/{id}` | propriétaire/HR | Lire / modifier / supprimer |
| GET/POST | `/api/company-objectives` | public / MANAGER-HR | Catalogue stratégique |
| POST | `/api/company-objectives/batch` | MANAGER/HR | Import batch stratégique |
| GET | `/api/team/members` | MANAGER/HR | Membres d'équipe |
| GET | `/api/team/stats` | MANAGER | Stats d'équipe (HR redirigé) |
| POST | `/api/analyze-smart` | authentifié | Analyse SMART unitaire |
| POST | `/api/analyze-alignment` | authentifié | Analyse d'alignement |
| POST | `/api/scan-excel` | authentifié | Prévisualisation structure Excel |
| POST | `/api/import-excel-analyze` | COLLAB/MANAGER/HR | Import + analyse (JSON) |
| POST | `/api/import-excel-export` | COLLAB/MANAGER/HR | Import + analyse (Excel enrichi) |
| GET | `/api/manager/objectives` | MANAGER | Objectifs d'équipe |
| GET | `/api/manager/team`, `/team-stats` | MANAGER | Équipe et statistiques |
| GET | `/api/manager/analysis-results` | MANAGER | Analyses privées Manager |
| POST | `/api/manager/analyze-personal` | MANAGER | Analyse de son objectif perso |
| POST | `/api/manager/analyze-objective/{id}` | MANAGER | Analyse d'un objectif d'équipe |
| GET | `/api/manager/export` | MANAGER | Export Excel/PDF équipe |
| GET | `/api/collab/analysis-results` | COLLAB | Analyses privées Collaborateur |
| POST | `/api/hr/analyze-personal` | HR | Analyse d'un objectif perso RH |
| GET | `/api/hr/analysis-results` | HR | Analyses personnelles RH |
| POST | `/api/hr/import-strategy` | HR | Import objectifs stratégiques |
| POST | `/api/hr/import-objectives` | HR | Import objectifs collaborateurs |
| POST | `/api/hr/analyze-batch` | HR | Analyse en lot (streaming SSE) |
| GET | `/api/hr/analytics` | HR | Tableaux de bord analytiques |
| GET | `/api/hr/objectives-details` | HR | Liste détaillée filtrée |
| GET | `/api/hr/export-excel`, `/export-pdf` | HR | Rapports RH |
| GET | `/api/hr/imports` | HR | Historique des imports |

> La liste interactive complète est disponible sur **`/docs`** (Swagger UI).

---

## 22. Tests

Suite **pytest** (31 tests), base **SQLite temporaire isolée** (jamais la production),
schéma créé via l'ORM (`init_db`) dans `app/tests/conftest.py` :

- `test_security.py` — hachage/vérif/migration, unicité des tokens, rate limiting, rejet 413.
- `test_audit.py` — écriture/lecture, filtrage anti-fuite, `session_ref` non réversible.
- `test_permissions.py` — contrôle de rôle, accès admin, périmètre de données par rôle.
- `test_auth_endpoints.py` — 401 sans token, login (succès/échec), `/auth/me`, register
  (anti-escalade HR/MANAGER), 429.
- `test_hr_import.py` — import Excel : mots de passe aléatoires distincts, pas de recréation
  d'un compte existant.

```bash
cd backend
python -m pytest -v   # tests sous app/tests/ (cf. pytest.ini)
```

---

## 23. Configuration (.env)

| Variable | Rôle |
|---|---|
| `SESSION_DURATION_HOURS` | Durée de validité d'une session |
| `PBKDF2_ITERATIONS` | Coût du hachage des mots de passe |
| `MAX_LOGIN_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | Anti brute-force |
| `DATABASE_PATH` | Chemin de la base SQLite |
| `ALLOWED_ORIGINS` | Origines CORS autorisées (jamais `*`) |
| `MAX_REQUEST_SIZE_MB` | Limite de taille des requêtes |
| `OLLAMA_URL` / `OLLAMA_MODEL` | Configuration de l'IA locale |
| `AUTH_PROVIDER` | `local` (défaut) ; SSO SAML actif dès que SP + IdP configurés |
| `SAML_*` | Configuration SSO SAML 2.0 (cf. `SSO_SAML.md`) |

---

## 24. Démarrage

```bash
# 1. Dépendances
pip install -r requirements.txt

# 2. Configuration
cp .env.example .env   # renseigner ALLOWED_ORIGINS (obligatoire au demarrage)

# 3. (IA) modèle Ollama
ollama create smart-qwen8 -f Modelfile && ollama serve

# 4. Backend
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

- API : `http://localhost:5001` — Swagger : `http://localhost:5001/docs` — Santé : `/health`.
- Au démarrage, `init_db()` crée automatiquement les tables manquantes (idempotent).

---

## 25. Évolutions prévues

- **Bascule SSO SAML 2.0 en production** : déjà implémenté (cf. `SSO_SAML.md`) ; renseigner
  SP + IdP dans `.env.local` — aucune modification des services/controllers requise.
- **Rôle `ADMIN` dédié** : aujourd'hui `HR` fait office d'admin (`require_admin`) ; un rôle
  `ADMIN` distinct est déjà anticipé dans le RBAC.
- **Module IA étendu** : challenger/améliorer automatiquement les objectifs (reformulations
  déjà produites par le modèle).
- **Migrations de schéma** : introduire Alembic si la base évolue au-delà du `create_all`.

---

*École Centrale Casablanca — Projet BMCI ObjectifSMART-AI — Backend FastAPI / SQLAlchemy.*
