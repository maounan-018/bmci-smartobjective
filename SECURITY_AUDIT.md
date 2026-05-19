# Audit de Sécurité — BMCI ObjectifSMART-AI
**Version analysée :** 2.0.0  
**Date de l'audit :** 18 mai 2026  
**Réalisé par :** Groupe 03 — École Centrale Casablanca  
**Contexte :** Outil interne BMCI (filiale BNP Paribas) — données RH et objectifs collaborateurs

---

## Résumé exécutif

L'audit de sécurité de la solution ObjectifSMART-AI a identifié **14 vulnérabilités**, dont **4 critiques** pouvant compromettre l'intégrité totale du système. La vulnérabilité la plus grave permet à n'importe quel utilisateur externe de s'octroyer des droits RH et d'accéder à l'ensemble des données des collaborateurs sans aucune restriction. Ces failles doivent être corrigées avant tout déploiement en environnement de production bancaire.

| Niveau | Nombre | Description |
|--------|--------|-------------|
| 🔴 Critique | 4 | Compromission totale possible |
| 🟠 Important | 5 | Exploitation nécessite conditions particulières |
| 🟡 Conformité | 5 | Exigences réglementaires bancaires non satisfaites |

---

## Table des matières

1. [Vulnérabilités Critiques](#1-vulnérabilités-critiques)
2. [Vulnérabilités Importantes](#2-vulnérabilités-importantes)
3. [Non-conformités Réglementaires](#3-non-conformités-réglementaires)
4. [Solutions Proposées](#4-solutions-proposées)
5. [Recommandation Stratégique — SSO Active Directory](#5-recommandation-stratégique--sso-active-directory)
6. [Plan de correction priorisé](#6-plan-de-correction-priorisé)

---

## 1. Vulnérabilités Critiques

---

### 🔴 CRIT-01 — Escalade de privilèges par auto-inscription

**Fichier :** `server.py` — lignes 316-320 et 634-687  
**Catégorie :** Broken Access Control (OWASP A01:2021)

#### Description

Le modèle `RegisterRequest` accepte un champ `role` envoyé librement par le client. Aucune validation côté serveur ne restreint les valeurs autorisées lors de l'inscription publique. Un attaquant peut s'inscrire avec le rôle `HR` ou `MANAGER` en manipulant simplement la requête HTTP.

```python
# Code actuel vulnérable
class RegisterRequest(BaseModel):
    role: str = "COLLAB"  # ← le client peut envoyer "HR" ou "MANAGER"
```

#### Scénario d'attaque

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"attaquant@ext.com","password":"test","name":"Hacker","role":"HR"}'
# Résultat : compte HR valide, accès à TOUS les objectifs de TOUS les collaborateurs
```

#### Impact

- Accès en lecture à l'ensemble des objectifs de tous les collaborateurs
- Accès aux analytics RH agrégées (performances, entités, managers)
- Accès aux fonctions d'export PDF/Excel de données RH sensibles
- Possibilité de créer et modifier des objectifs stratégiques d'entreprise

#### Sévérité : CVSS 9.8 / 10 — Critique

---

### 🔴 CRIT-02 — Hachage des mots de passe sans sel (SHA-256 brut)

**Fichier :** `server.py` — ligne 381-382  
**Catégorie :** Cryptographic Failures (OWASP A02:2021)

#### Description

Les mots de passe sont hachés avec SHA-256 sans sel aléatoire. SHA-256 est un algorithme de hachage général, non conçu pour les mots de passe. Il est extrêmement rapide (des milliards de calculs par seconde sur GPU), ce qui le rend vulnérable aux attaques par force brute et aux rainbow tables.

```python
# Code actuel vulnérable
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
```

Les mots de passe par défaut codés en dur (`manager123`, `hr123`) sont déjà présents dans toutes les rainbow tables publiques.

#### Impact

En cas de vol de la base de données SQLite (fichier `objectifsmart.db`) :
- Tous les mots de passe courants retrouvés en quelques secondes
- Les comptes par défaut (`manager123`, `hr123`) immédiatement compromis
- Impossibilité de distinguer deux utilisateurs ayant le même mot de passe (absence de sel)

#### Sévérité : CVSS 8.1 / 10 — Critique

---

### 🔴 CRIT-03 — Endpoint public exposant l'organigramme interne

**Fichier :** `server.py` — lignes 625-632  
**Catégorie :** Security Misconfiguration (OWASP A05:2021)

#### Description

L'endpoint `/api/managers` ne requiert aucune authentification. Il retourne la liste complète des managers de la BMCI avec leurs noms, adresses email professionnelles et équipes, accessible sans aucun token depuis n'importe quelle machine sur le réseau.

```python
# Code actuel — aucune authentification requise
@app.get("/api/managers")
def list_managers():
    cursor.execute("SELECT id, name, email, team FROM users WHERE role = 'MANAGER'")
    return {"managers": [dict(row) for row in cursor.fetchall()]}
```

#### Impact

- Fuite de l'organigramme interne de la BMCI (noms, emails, rattachements)
- Données exploitables pour des attaques de phishing ciblées (spear phishing)
- Violation de la politique de confidentialité des données RH

#### Sévérité : CVSS 7.5 / 10 — Critique

---

### 🔴 CRIT-04 — Absence de protection contre la force brute

**Fichier :** `server.py` — ligne 689  
**Catégorie :** Identification and Authentication Failures (OWASP A07:2021)

#### Description

L'endpoint `/api/auth/login` n'implémente aucun mécanisme de limitation de débit (rate limiting), aucun verrouillage de compte, et aucune détection d'anomalie. Un attaquant peut tenter un nombre illimité de combinaisons email/mot de passe sans aucune conséquence.

#### Impact

- Attaque par dictionnaire sur n'importe quel compte en quelques minutes
- Avec 1 000 requêtes/minute, un mot de passe de 8 caractères courants peut être trouvé en heures
- Aucune alerte déclenchée, aucune trace d'audit

#### Sévérité : CVSS 7.3 / 10 — Critique

---

## 2. Vulnérabilités Importantes

---

### 🟠 IMP-01 — Token d'authentification stocké dans localStorage

**Fichier :** `services/authService.ts` — ligne 49  
**Catégorie :** Cryptographic Failures / XSS (OWASP A02 + A03)

#### Description

Le token de session est stocké dans `localStorage`, qui est accessible par tout code JavaScript s'exécutant sur la page. En cas de vulnérabilité XSS (injection de script), le token peut être volé et réutilisé depuis n'importe quelle machine.

```typescript
// Code actuel vulnérable
localStorage.setItem(TOKEN_KEY, token);
```

Un token stocké dans un cookie `httpOnly` est totalement inaccessible au JavaScript, même en cas de XSS réussi.

#### Impact

- Vol de session sans interaction utilisateur via XSS
- Usurpation d'identité persistante (token valide 24h)

---

### 🟠 IMP-02 — CORS ouvert à toutes les origines

**Fichier :** `server.py` — ligne 68  
**Catégorie :** Security Misconfiguration (OWASP A05)

#### Description

```python
allow_origins=["*"]  # accepte les requêtes de n'importe quel domaine
```

N'importe quel site web tiers peut effectuer des requêtes authentifiées vers l'API BMCI au nom d'un utilisateur connecté (attaque Cross-Site Request Forgery cross-origin).

---

### 🟠 IMP-03 — Aucune politique de complexité des mots de passe

**Fichier :** `server.py` — `RegisterRequest`  
**Catégorie :** Authentication Failures (OWASP A07)

#### Description

Aucune validation n'est appliquée sur le mot de passe lors de l'inscription. Un utilisateur peut s'inscrire avec le mot de passe `a` (1 caractère). Pour un outil bancaire, les exigences minimales sont : 12 caractères, majuscule, minuscule, chiffre, caractère spécial.

---

### 🟠 IMP-04 — En-têtes de sécurité HTTP absents

**Fichier :** `server.py` — middleware CORS  
**Catégorie :** Security Misconfiguration (OWASP A05)

#### Description

L'API ne retourne aucun des en-têtes de sécurité standard. Les suivants sont manquants :

| En-tête | Rôle |
|---------|------|
| `Strict-Transport-Security` | Force l'utilisation de HTTPS |
| `X-Frame-Options: DENY` | Bloque le clickjacking via iframes |
| `X-Content-Type-Options: nosniff` | Bloque le MIME sniffing |
| `Content-Security-Policy` | Restreint les sources de scripts autorisées |
| `Referrer-Policy: no-referrer` | Empêche la fuite d'URL dans les referers |

---

### 🟠 IMP-05 — Logs de debug exposant des données sensibles

**Fichier :** `server.py` — ligne 585  
**Catégorie :** Security Logging and Monitoring Failures (OWASP A09)

#### Description

```python
print(f"[DEBUG] Raw response: {text[:500]}...")
```

Le contenu brut des réponses IA (qui inclut les objectifs professionnels des collaborateurs) est affiché dans la console du serveur. En production, ces données confidentielles ne doivent jamais apparaître dans des logs non structurés.

---

## 3. Non-conformités Réglementaires

---

### 🟡 REG-01 — Absence d'audit log des actions sensibles

**Exigences :** ISO 27001 (A.12.4), DORA (Article 10), Bank Al-Maghrib Directive 1/W/2017

Aucune action n'est tracée : connexions, déconnexions, accès aux données, exports, modifications. Une banque doit pouvoir répondre à la question "qui a accédé à quoi, quand, depuis quelle adresse IP" pour toute donnée sensible.

---

### 🟡 REG-02 — Durée de session excessive

**Fichier :** `server.py` — ligne 79 : `TOKEN_EXPIRY_HOURS = 24`

Pour un outil interne bancaire, la politique standard est une session active de **30 minutes maximum** avec renouvellement automatique sur activité. Une session de 24h laisse une fenêtre d'exploitation trop large en cas de vol de token.

---

### 🟡 REG-03 — Base de données non chiffrée au repos

**Fichier :** `objectifsmart.db`

La base SQLite est un fichier non chiffré sur le disque. Tout accès physique ou distant au serveur (partage réseau, sauvegarde, incident) expose directement toutes les données. La réglementation bancaire exige le chiffrement des données au repos.

---

### 🟡 REG-04 — Comptes par défaut avec mots de passe faibles codés en dur

**Fichier :** `server.py` — lignes 285-303

```python
# Mots de passe en clair dans le code source
("manager123", ...)
("hr123", ...)
```

Des credentials ne doivent jamais apparaître en clair dans le code source. Ces comptes par défaut doivent être supprimés avant la mise en production, ou provisionnés via des variables d'environnement sécurisées.

---

### 🟡 REG-05 — Absence de mécanisme de révocation d'accès immédiat

Quand un employé quitte la BMCI, son compte doit être désactivé instantanément. Actuellement, aucun mécanisme de désactivation de compte n'existe : la suppression physique de l'enregistrement en base est la seule option, ce qui détruit aussi l'historique des données — non conforme aux obligations de conservation.

---

## 4. Solutions Proposées

---

### Solution A — Correction CRIT-01 : Bloquer l'escalade de rôle

**Effort :** 15 minutes | **Impact :** Élimine la vulnérabilité la plus critique

**Option 1 — Restreindre l'auto-inscription aux collaborateurs uniquement (recommandé court terme)**

```python
@app.post("/api/auth/register")
def register(request: RegisterRequest):
    # Seul le rôle COLLAB est autorisé en auto-inscription
    if request.role != "COLLAB":
        raise HTTPException(
            status_code=403,
            detail="L'auto-inscription est réservée aux collaborateurs. "
                   "Contactez votre administrateur IT pour créer un compte Manager ou RH."
        )
    # ... reste du code inchangé
```

**Option 2 — Endpoint admin protégé pour la création des managers/RH (recommandé long terme)**

```python
@app.post("/api/admin/users")
def create_privileged_user(
    request: RegisterRequest,
    current_user: dict = Depends(get_current_user)
):
    # Seul un RH existant peut créer des comptes Manager ou RH
    if current_user['role'] != 'HR':
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs RH.")
    if request.role not in ("COLLAB", "MANAGER", "HR"):
        raise HTTPException(status_code=400, detail="Rôle invalide.")
    # ... création du compte
```

---

### Solution B — Correction CRIT-02 : Remplacer SHA-256 par bcrypt

**Effort :** 1 heure (migration incluse) | **Impact :** Protège tous les mots de passe existants et futurs

**Installation :**
```bash
pip install bcrypt
```

**Nouveau code :**
```python
import bcrypt

def hash_password(password: str) -> str:
    """bcrypt avec sel automatique et 12 rounds (standard bancaire)"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comparaison sécurisée résistante aux timing attacks"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

**Modification du login (suppression de la comparaison SQL directe) :**
```python
@app.post("/api/auth/login")
def login(request: LoginRequest):
    with db_session() as conn:
        cursor = conn.cursor()
        # Récupérer l'utilisateur par email uniquement
        cursor.execute("SELECT * FROM users WHERE email = ?", (request.email,))
        user = cursor.fetchone()

        # Vérification du mot de passe hors SQL (résistant aux timing attacks)
        if not user or not verify_password(request.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")
```

**Script de migration des comptes existants :**
```python
def migrate_passwords_to_bcrypt():
    """À exécuter une seule fois pour migrer les hashes SHA-256 existants"""
    # Marquer les comptes à migrer — ils devront réinitialiser leur mot de passe
    with db_session() as conn:
        conn.execute("ALTER TABLE users ADD COLUMN hash_algo TEXT DEFAULT 'sha256'")
        conn.execute("UPDATE users SET hash_algo = 'sha256'")
    print("Migration : les utilisateurs existants devront réinitialiser leur mot de passe.")
```

---

### Solution C — Correction CRIT-03 : Protéger l'endpoint managers

**Effort :** 5 minutes

```python
@app.get("/api/managers")
def list_managers(current_user: dict = Depends(get_current_user)):
    """Liste les managers — authentification requise"""
    with db_session() as conn:
        cursor = conn.cursor()
        # Retourner uniquement id et name (pas l'email) pour les non-RH
        if current_user['role'] == 'HR':
            cursor.execute("SELECT id, name, email, team FROM users WHERE role = 'MANAGER'")
        else:
            cursor.execute("SELECT id, name, team FROM users WHERE role = 'MANAGER'")
        return {"managers": [dict(row) for row in cursor.fetchall()]}
```

---

### Solution D — Correction CRIT-04 : Rate limiting et verrouillage de compte

**Effort :** 2 heures

**Installation :**
```bash
pip install slowapi
```

**Rate limiting par IP :**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/auth/login")
@limiter.limit("5/minute")          # 5 tentatives par minute par IP
@limiter.limit("20/hour")           # 20 tentatives par heure par IP
def login(request: Request, body: LoginRequest):
    ...
```

**Verrouillage de compte (ajout de colonnes en base) :**
```sql
ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until TEXT DEFAULT NULL;
```

```python
def check_account_locked(user: dict):
    if user.get('locked_until'):
        locked_until = datetime.fromisoformat(user['locked_until'])
        if datetime.now() < locked_until:
            remaining = int((locked_until - datetime.now()).total_seconds() / 60)
            raise HTTPException(
                status_code=423,
                detail=f"Compte verrouillé suite à trop de tentatives échouées. "
                       f"Réessayez dans {remaining} minutes ou contactez votre manager."
            )

def record_failed_attempt(user_id: str):
    with db_session() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?",
            (user_id,)
        )
        row = conn.execute(
            "SELECT failed_attempts FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row['failed_attempts'] >= 5:
            locked_until = (datetime.now() + timedelta(minutes=30)).isoformat()
            conn.execute(
                "UPDATE users SET locked_until = ? WHERE id = ?",
                (locked_until, user_id)
            )

def reset_failed_attempts(user_id: str):
    with db_session() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
            (user_id,)
        )
```

---

### Solution E — Correction IMP-01 : Cookies httpOnly

**Effort :** 3 heures (backend + frontend)

**Backend — retourner un cookie sécurisé :**
```python
from fastapi import Response

@app.post("/api/auth/login")
def login(request: LoginRequest, response: Response):
    # ... vérification ...
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,       # inaccessible au JavaScript
        secure=True,         # HTTPS uniquement (désactiver en dev local)
        samesite="strict",   # protection CSRF native
        max_age=3600 * 8,    # 8 heures
        path="/api"          # restreindre le scope du cookie
    )
    return {"success": True, "user": {...}}

@app.post("/api/auth/logout")
def logout(response: Response, current_user: dict = Depends(get_current_user)):
    response.delete_cookie(key="session_token", path="/api")
    with db_session() as conn:
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (current_user['id'],))
    return {"success": True}
```

**Middleware de lecture du cookie :**
```python
def get_current_user(
    authorization: Optional[str] = Header(None),
    session_token: Optional[str] = Cookie(None)
):
    """Accepte cookie httpOnly ou header Authorization (rétrocompatibilité)"""
    token = session_token or (authorization.replace("Bearer ", "") if authorization else None)
    if not token:
        raise HTTPException(status_code=401, detail="Non authentifié.")
    # ... reste de la validation inchangé
```

**Frontend — supprimer le stockage localStorage :**
```typescript
// authService.ts — retirer complètement la gestion manuelle du token
// Le cookie httpOnly est géré automatiquement par le navigateur

async login(credentials: LoginCredentials) {
    const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        credentials: 'include',  // ← indispensable pour envoyer/recevoir les cookies
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
    });
    // Ne plus stocker de token — le cookie est géré par le navigateur
}
```

---

### Solution F — Correction IMP-02 : CORS restrictif

**Effort :** 15 minutes

```python
import os

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000"  # valeur de développement par défaut
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # ex: ["https://smartobjective.bmci.co.ma"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],  # plus besoin d'Authorization avec les cookies
)
```

---

### Solution G — Correction IMP-03 : Politique de mots de passe

**Effort :** 30 minutes

```python
import re
from pydantic import validator

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "COLLAB"
    manager_id: Optional[str] = None

    @validator('password')
    def validate_password_complexity(cls, v):
        errors = []
        if len(v) < 12:
            errors.append("au moins 12 caractères")
        if not re.search(r'[A-Z]', v):
            errors.append("au moins une lettre majuscule")
        if not re.search(r'[a-z]', v):
            errors.append("au moins une lettre minuscule")
        if not re.search(r'\d', v):
            errors.append("au moins un chiffre")
        if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>?/\\|`~]', v):
            errors.append("au moins un caractère spécial (!@#$...)")
        if errors:
            raise ValueError(f"Mot de passe insuffisant : {', '.join(errors)}.")
        return v

    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2 or len(v) > 100:
            raise ValueError("Le nom doit contenir entre 2 et 100 caractères.")
        return v.strip()
```

---

### Solution H — Correction IMP-04 : En-têtes de sécurité

**Effort :** 30 minutes

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

### Solution I — Audit log des actions sensibles (Conformité bancaire)

**Effort :** 2 heures

**Création de la table :**
```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id          TEXT PRIMARY KEY,
    event       TEXT NOT NULL,
    user_id     TEXT,
    user_email  TEXT,
    ip_address  TEXT,
    user_agent  TEXT,
    details     TEXT,
    severity    TEXT DEFAULT 'INFO',
    timestamp   TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_event ON audit_logs(event);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
```

**Fonction d'audit :**
```python
import uuid

AUDIT_EVENTS = {
    "LOGIN_SUCCESS":      "INFO",
    "LOGIN_FAILURE":      "WARNING",
    "LOGOUT":             "INFO",
    "ACCOUNT_LOCKED":     "WARNING",
    "REGISTER":           "INFO",
    "OBJECTIVE_CREATED":  "INFO",
    "OBJECTIVE_ACCESSED": "INFO",
    "OBJECTIVE_DELETED":  "WARNING",
    "HR_EXPORT":          "WARNING",
    "HR_IMPORT":          "WARNING",
    "UNAUTHORIZED_ACCESS":"CRITICAL",
}

def audit_log(event: str, request, user: dict = None, details: dict = None):
    severity = AUDIT_EVENTS.get(event, "INFO")
    with db_session() as conn:
        conn.execute('''
            INSERT INTO audit_logs (id, event, user_id, user_email, ip_address, user_agent, details, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()),
            event,
            user['id'] if user else None,
            user['email'] if user else None,
            request.client.host if request.client else "unknown",
            request.headers.get("user-agent", "unknown")[:200],
            json.dumps(details or {}),
            severity
        ))
```

**Utilisation dans les endpoints critiques :**
```python
# Exemples d'intégration
audit_log("LOGIN_SUCCESS", request, user=user)
audit_log("LOGIN_FAILURE", request, details={"email": request.email})
audit_log("ACCOUNT_LOCKED", request, details={"user_id": user['id']})
audit_log("HR_EXPORT", request, user=current_user, details={"format": "pdf", "records": count})
audit_log("UNAUTHORIZED_ACCESS", request, user=current_user, details={"endpoint": str(request.url)})
```

---

### Solution J — Variables d'environnement pour les secrets

**Effort :** 30 minutes

**Fichier `.env` (ne jamais versionner dans git) :**
```env
SECRET_KEY=<générer avec: python -c "import secrets; print(secrets.token_hex(32))">
DEFAULT_HR_PASSWORD=<mot de passe fort généré>
DEFAULT_MANAGER_PASSWORD=<mot de passe fort généré>
ALLOWED_ORIGINS=http://localhost:3000
TOKEN_EXPIRY_HOURS=8
DB_ENCRYPTION_KEY=<clé de chiffrement>
```

**Lecture sécurisée dans `server.py` :**
```python
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY manquante. Configurez le fichier .env.")

TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "8"))
```

**Ajout au `.gitignore` :**
```
.env
*.db
__pycache__/
```

---

## 5. Recommandation Stratégique — SSO Active Directory

Pour un déploiement en production dans un environnement bancaire, la solution de sécurité optimale est l'**intégration SSO (Single Sign-On) avec l'Active Directory de la BMCI**.

### Architecture cible

```
Collaborateur BMCI
       │
       │ Saisit ses identifiants Windows habituels
       ▼
┌─────────────────────┐
│  Page Login BMCI    │──── Redirige vers ──────►│ Azure AD / LDAP BMCI │
│  ObjectifSMART      │◄─── Token OIDC ──────────│ (authentification     │
└─────────────────────┘                           │  corporate)          │
       │                                          └──────────────────────┘
       │ Vérifie le token, extrait le rôle depuis AD
       ▼
┌─────────────────────┐
│  ObjectifSMART-AI   │
│  (pas de gestion    │
│   de mot de passe)  │
└─────────────────────┘
```

### Avantages pour la BMCI

| Aspect | Bénéfice |
|--------|----------|
| **Gestion des départs** | Désactivation du compte AD = accès révoqué instantanément dans tous les outils |
| **MFA** | Le MFA déjà en place sur le réseau BMCI s'applique automatiquement |
| **Mots de passe** | Aucun mot de passe supplémentaire — même identifiant que le poste Windows |
| **Audit** | Les connexions s'intègrent dans le SIEM de la banque |
| **Conformité** | Satisfait nativement DORA, ISO 27001, exigences Bank Al-Maghrib |
| **Rôles** | Les groupes AD (ex: `GRP-BMCI-RH`, `GRP-BMCI-MANAGERS`) mappent directement aux rôles |

### Implémentation avec python-jose + LDAP3

```bash
pip install authlib python-jose[cryptography] ldap3
```

```python
# Authentification LDAP Active Directory
from ldap3 import Server, Connection, ALL, NTLM

def authenticate_ldap(username: str, password: str) -> dict:
    """Authentifie un utilisateur via l'Active Directory BMCI"""
    server = Server(os.getenv("LDAP_SERVER"), get_info=ALL)
    try:
        conn = Connection(
            server,
            user=f"BMCI\\{username}",
            password=password,
            authentication=NTLM
        )
        if not conn.bind():
            return None

        # Récupérer les attributs AD (nom, email, groupe = rôle)
        conn.search(
            search_base=os.getenv("LDAP_BASE_DN"),
            search_filter=f"(sAMAccountName={username})",
            attributes=['displayName', 'mail', 'memberOf']
        )
        entry = conn.entries[0]
        role = map_ad_groups_to_role(entry.memberOf.values)
        return {
            "name": str(entry.displayName),
            "email": str(entry.mail),
            "role": role
        }
    except Exception:
        return None

def map_ad_groups_to_role(groups: list) -> str:
    """Mappe les groupes Active Directory aux rôles applicatifs"""
    group_names = [g.upper() for g in groups]
    if any("GRP-BMCI-RH" in g for g in group_names):
        return "HR"
    if any("GRP-BMCI-MANAGERS" in g for g in group_names):
        return "MANAGER"
    return "COLLAB"
```

---

## 6. Plan de correction priorisé

### Phase 1 — Urgences (à corriger avant tout accès utilisateur)

| # | Action | Fichier | Durée estimée | Solution |
|---|--------|---------|--------------|----------|
| 1 | Bloquer l'escalade de rôle | `server.py` | 15 min | Solution A |
| 2 | Ajouter l'auth sur `/api/managers` | `server.py` | 5 min | Solution C |
| 3 | Remplacer SHA-256 par bcrypt | `server.py` | 1h | Solution B |
| 4 | Ajouter le rate limiting | `server.py` | 1h | Solution D |

**Durée totale Phase 1 : ~2h30**

---

### Phase 2 — Renforcement (avant déploiement pilote)

| # | Action | Fichier(s) | Durée estimée | Solution |
|---|--------|-----------|--------------|----------|
| 5 | Migrer vers cookies httpOnly | `server.py` + `authService.ts` | 3h | Solution E |
| 6 | Restreindre le CORS | `server.py` | 15 min | Solution F |
| 7 | Ajouter la politique de mots de passe | `server.py` | 30 min | Solution G |
| 8 | Ajouter les en-têtes de sécurité | `server.py` | 30 min | Solution H |
| 9 | Externaliser les secrets dans `.env` | `server.py` | 30 min | Solution J |

**Durée totale Phase 2 : ~5h**

---

### Phase 3 — Conformité bancaire (avant déploiement production)

| # | Action | Durée estimée | Solution |
|---|--------|--------------|----------|
| 10 | Implémenter l'audit log complet | 2h | Solution I |
| 11 | Réduire la durée de session à 8h + inactivité 30 min | 1h | — |
| 12 | Chiffrement de la base SQLite (SQLCipher) ou migration PostgreSQL | 1 jour | — |
| 13 | Verrouillage de compte (5 tentatives → 30 min) | 1h | Solution D |
| 14 | Désactiver les comptes par défaut | 15 min | Solution J |

**Durée totale Phase 3 : ~2 jours**

---

### Phase 4 — Objectif production complète (recommandé)

| # | Action | Durée estimée | Solution |
|---|--------|--------------|----------|
| 15 | Intégration SSO Active Directory BMCI | 2-3 jours | Solution SSO |
| 16 | Passage HTTPS avec certificat TLS interne BMCI | 1 jour | — |
| 17 | Tests de pénétration par l'équipe sécurité BMCI | Variable | — |

---

## Références

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [NIST Password Guidelines SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [DORA — Digital Operational Resilience Act (UE 2022/2554)](https://www.eba.europa.eu/regulation-and-policy/operational-resilience/digital-operational-resilience-act-dora)
- [Bank Al-Maghrib — Directive 1/W/2017 relative à la sécurité des systèmes d'information](https://www.bkam.ma)
- [ISO/IEC 27001:2022 — Systèmes de management de la sécurité de l'information](https://www.iso.org/standard/27001)
- [bcrypt — Password Hashing](https://pypi.org/project/bcrypt/)
- [SlowAPI — Rate Limiting for FastAPI](https://github.com/laurentS/slowapi)
- [python-ldap3 — Active Directory Integration](https://ldap3.readthedocs.io/)

---

*Document produit dans le cadre du Projet Innovation — École Centrale Casablanca 2024-2025*  
*Encadrante : Mme Annoukoubi Maha | Entreprise partenaire : BMCI*
