# Analyse du Système d'Authentification par Carte BMCI
## Et Propositions d'Intégration avec ObjectifSMART-AI

**Document préparé par :** Groupe 03 — École Centrale Casablanca  
**À l'attention de :** Lompo Bampalou Ernest (Chef d'équipe)  
**Date :** Mai 2026  
**Contexte :** Amélioration du système d'authentification de ObjectifSMART-AI

---

## Table des matières

1. [Comprendre le système de carte BMCI](#1-comprendre-le-système-de-carte-bmci)
2. [Comment fonctionne le verrouillage automatique](#2-comment-fonctionne-le-verrouillage-automatique)
3. [Pourquoi certains employés peuvent installer Python et d'autres non](#3-pourquoi-certains-employés-peuvent-installer-python-et-dautres-non)
4. [La base de données derrière tout ça — Active Directory](#4-la-base-de-données-derrière-tout-ça--active-directory)
5. [Options d'intégration avec ObjectifSMART-AI](#5-options-dintégration-avec-objectifsmart-ai)
6. [Recommandation finale](#6-recommandation-finale)
7. [Plan d'implémentation](#7-plan-dimplémentation)

---

## 1. Comprendre le système de carte BMCI

### 1.1 Qu'est-ce que c'est ?

La carte que chaque employé BMCI utilise est appelée une **carte à puce PKI** (Public Key Infrastructure). C'est une carte intelligente qui contient un microprocesseur et qui remplace le nom d'utilisateur + mot de passe classique.

En général, les grandes banques comme la BMCI utilisent un système qui combine **deux technologies sur la même carte physique** :

```
┌─────────────────────────────────────────────────────────┐
│                   CARTE EMPLOYÉ BMCI                    │
│                                                         │
│  ┌─────────────────────┐   ┌─────────────────────────┐ │
│  │  PUCE CONTACT       │   │  PUCE SANS CONTACT      │ │
│  │  (PKI / Smart Card) │   │  (RFID / Mifare)        │ │
│  │                     │   │                         │ │
│  │  - Certificat X.509 │   │  - Identifiant badging  │ │
│  │  - Clé privée RSA   │   │  - Accès portes/entrées │ │
│  │  - PIN de la carte  │   │  - Pointage entrée/sortie│ │
│  │                     │   │                         │ │
│  │  Utilisée pour :    │   │  Utilisée pour :        │ │
│  │  → Démarrer le PC   │   │  → Badger à l'entrée    │ │
│  │  → Se connecter aux │   │  → Ouvrir les portes    │ │
│  │    logiciels        │   │  → Présence/absence     │ │
│  └─────────────────────┘   └─────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Les composants techniques du système

Voici tous les acteurs du système, du plus visible au plus invisible :

| Composant | Rôle | Où ça tourne |
|-----------|------|--------------|
| **La carte physique** | Stocke le certificat et la clé privée | Dans la poche de l'employé |
| **Le lecteur de carte** | Interface entre la carte et le PC | Sur chaque poste de travail |
| **PC/SC (Personal Computer / Smart Card)** | Pilote Windows qui gère la communication carte-PC | Sur chaque PC |
| **PKCS#11 / CryptoAPI** | Standard de cryptographie qui lit la carte | Sur chaque PC |
| **Active Directory (AD)** | Base de données centrale de tous les employés | Sur les serveurs BMCI |
| **Kerberos / NTLM** | Protocole d'authentification réseau | Sur les serveurs BMCI |
| **Group Policy Objects (GPO)** | Règles de droits et restrictions | Sur les serveurs BMCI |
| **PKI (Autorité de Certification)** | Génère et valide les certificats des cartes | Sur les serveurs BMCI |

### 1.3 Ce qui se passe exactement quand un employé insère sa carte

```
Employé insère la carte
         │
         ▼
[PC/SC] Le lecteur détecte la carte
         │
         ▼
[Windows] Demande le PIN de la carte à l'employé
         │
         ▼
[PKCS#11] Lit le certificat X.509 stocké dans la carte
         │
         ▼
[Kerberos] Envoie le certificat au contrôleur de domaine AD
         │
         ▼
[Active Directory] Vérifie :
   - Le certificat est-il valide (non expiré, non révoqué) ?
   - À quel compte employé correspond ce certificat ?
   - Quels groupes et droits a cet employé ?
         │
         ▼
[Windows] Session ouverte avec l'identité de l'employé
         │
         ▼
[GPO] Application automatique des droits et restrictions
   - Accès réseau autorisés
   - Logiciels autorisés / bloqués
   - Possibilité ou non d'installer des bibliothèques
```

### 1.4 Pourquoi les logiciels se configurent automatiquement sur chaque PC — Roaming Profiles

Tu as mentionné que "les logiciels installés sur un PC sont déjà configurés grâce aux identifiants de la carte". Voici l'explication technique de ce mécanisme : ce sont les **Roaming Profiles** (Profils itinérants) d'Active Directory.

**Ce que c'est :** Quand un employé se connecte avec sa carte sur **n'importe quel PC** du réseau BMCI, Windows va chercher sur un serveur central son profil personnel (bureau, paramètres, favoris, configuration des logiciels). Ce profil est stocké dans AD et synchronisé à chaque connexion.

```
PC de l'employé A (son bureau habituel)
        │  Carte insérée
        ▼
Active Directory
  └── Profil de Chaimaa ABID :
        - Paramètres Outlook configurés avec sa boîte mail
        - Raccourcis sur le bureau
        - Configuration SAP, outils RH
        - GPO : droits RH appliqués

PC de l'employé B (salle de réunion, autre bureau)
        │  Même carte insérée
        ▼
Active Directory
  └── MÊME profil de Chaimaa ABID chargé automatiquement
        → Mêmes logiciels configurés, mêmes droits, même bureau
```

**Impact pour ObjectifSMART-AI :** Si on intègre l'authentification AD, l'application se comportera exactement comme ça — l'employé accède à son espace personnalisé (Collaborateur/Manager/RH) depuis n'importe quel PC du réseau BMCI, sans reconfiguration.

---

## 2. Comment fonctionne le verrouillage automatique

Quand l'employé **retire sa carte**, Windows détecte immédiatement l'événement via le service `SCardSvr` (Smart Card Service). Une règle de sécurité configurée dans les GPO (Group Policy) de la BMCI déclenche automatiquement le verrouillage.

La règle en question s'appelle : **"Interactive logon: Smart card removal behavior"**

Elle peut être configurée sur :
- `Lock Workstation` → verrouille l'écran (probablement ce que fait la BMCI)
- `Force Logoff` → déconnecte complètement
- `Disconnect if a Remote Desktop Services session`

C'est pourquoi **dès que la carte est retirée, même 1 seconde, le PC se verrouille**. C'est une décision de sécurité délibérée de la BMCI : si l'employé s'éloigne de son poste, personne ne peut accéder à ses données.

### 2.1 Lien entre le verrouillage du PC et la session ObjectifSMART-AI

Point critique à implémenter : quand le PC se verrouille (carte retirée), la session ObjectifSMART-AI devrait également expirer automatiquement pour ne pas laisser un espace de travail ouvert et accessible à d'autres.

**Comment faire :**

```
Carte retirée → PC verrouillé
        │
        ▼
Session Windows suspendue (token Kerberos inactif)
        │
        ▼
ObjectifSMART-AI : token de session expire côté serveur
(grâce au TOKEN_EXPIRY_HOURS = 8h + inactivité détectée)
        │
        ▼
Quand l'employé remet sa carte et déverrouille le PC
→ Le navigateur recharge ObjectifSMART-AI
→ Le token est expiré → retour à la page de connexion
→ L'employé se ré-authentifie (avec sa carte/session Windows)
```

Avec l'intégration Kerberos (Option B), ce processus est encore plus propre : quand le token Windows expire, le token ObjectifSMART-AI expire aussi automatiquement.

---

## 3. Pourquoi certains employés peuvent installer Python et d'autres non

Ce n'est **pas la carte** qui décide directement de ça. La carte sert uniquement à **identifier qui tu es**. Ce sont les **Group Policy Objects (GPO)** d'Active Directory qui décident de ce que tu peux faire.

### Comment ça fonctionne :

```
Active Directory
│
├── Groupe : GRP-BMCI-IT-DEVELOPERS
│     └── GPO : Peut installer des logiciels, bibliothèques Python, etc.
│
├── Groupe : GRP-BMCI-RH
│     └── GPO : Accès aux outils RH, lecture seule sur certains dossiers
│
├── Groupe : GRP-BMCI-MANAGERS
│     └── GPO : Accès aux rapports d'équipe, outils de reporting
│
└── Groupe : GRP-BMCI-COLLABORATEURS
      └── GPO : Accès basique, pas d'installation de logiciels
```

Quand l'employé s'authentifie avec sa carte, Active Directory sait immédiatement dans quels groupes il se trouve. Windows applique alors automatiquement les GPO correspondantes à sa session.

**Conclusion :** Les restrictions ne sont pas dans la carte, elles sont dans la base de données Active Directory. C'est cette même base de données qu'on veut utiliser pour ObjectifSMART-AI.

---

## 4. La base de données derrière tout ça — Active Directory

### 4.1 Qu'est-ce qu'Active Directory ?

Active Directory (AD) est le **cœur du système d'identité de la BMCI**. C'est une base de données Microsoft qui centralise :

- La liste de tous les employés (nom, prénom, email, identifiant)
- Les groupes d'appartenance (RH, Manager, IT, Collaborateur, etc.)
- Les mots de passe hashés
- Les certificats liés aux cartes
- Les droits et restrictions (GPO)
- La structure hiérarchique (qui est le manager de qui)

### 4.2 Structure typique des données d'un employé dans AD

```
DN: CN=Chaimaa ABID,OU=RH,OU=Direction,DC=bmci,DC=co,DC=ma

Attributs :
  sAMAccountName  : cabid
  displayName     : Chaimaa ABID
  mail            : c.abid@bmci.co.ma
  department      : Ressources Humaines
  title           : Responsable RH
  manager         : CN=Directeur RH,OU=Direction,DC=bmci,DC=co,DC=ma
  memberOf        : GRP-BMCI-RH
                    GRP-BMCI-ALL-EMPLOYEES
  userCertificate : [certificat X.509 lié à sa carte]
  employeeID      : 00847
```

### 4.3 Le champ `manager` dans AD résout le problème de sélection du manager

Point crucial pour ObjectifSMART-AI : dans notre application actuelle, quand un collaborateur s'inscrit, il doit **manuellement sélectionner son manager** dans une liste déroulante. C'est un point faible UX et un risque d'erreur.

**Avec Active Directory, ce problème disparaît complètement.** L'attribut `manager` dans le profil AD de chaque employé contient directement le DN (identifiant unique) de son manager hiérarchique. Cette information est maintenue à jour par la DSI/RH BMCI à chaque mouvement de personnel.

```python
# Lors de l'authentification LDAP, le manager est récupéré automatiquement :
entry.manager  
# → "CN=Youssef BENCHEIKH,OU=Digital,DC=bmci,DC=co,DC=ma"

# On extrait le sAMAccountName du manager pour le retrouver dans notre base :
manager_username = extraire_username_depuis_dn(str(entry.manager))
# → "ybencheikh"
```

**Résultat :** Le collaborateur n'a plus jamais besoin de choisir son manager. L'application le récupère directement depuis AD et l'associe automatiquement.

### 4.4 Protocoles pour interroger Active Directory

| Protocole | Description | Usage |
|-----------|-------------|-------|
| **LDAP** (port 389) | Requêtes pour lire les données des employés | Authentification + récupération du profil |
| **LDAPS** (port 636) | LDAP chiffré (TLS) | Version sécurisée recommandée en production |
| **Kerberos** (port 88) | Authentification SSO réseau | Session Windows transparente |
| **NTLM** | Authentification Windows legacy | Compatibilité anciens systèmes |
| **OIDC/SAML** (via ADFS) | Fédération d'identité web | Applications web modernes |

---

## 5. Options d'intégration avec ObjectifSMART-AI

Voici les 4 voies possibles, classées de la plus simple à la plus avancée.

---

### Option A — Authentification LDAP (recommandée à court terme)

**Principe :** L'employé saisit son identifiant BMCI (ex: `cabid`) et son mot de passe Windows dans ObjectifSMART-AI. L'application vérifie ces identifiants directement dans Active Directory via LDAP. Si c'est valide, elle récupère automatiquement le nom, email, département et rôle de l'employé.

```
Employé saisit : cabid / MonMotDePasseWindows
        │
        ▼
ObjectifSMART-AI (FastAPI)
        │
        │  Requête LDAP : "Est-ce que cabid/password est valide ?"
        ▼
Active Directory BMCI
        │
        │  Réponse : "Oui, et voici son profil :
        │    - Nom : Chaimaa ABID
        │    - Département : RH
        │    - Groupes : GRP-BMCI-RH"
        ▼
ObjectifSMART-AI attribue automatiquement le rôle HR
et affiche le dashboard RH
```

**Avantages :**
- Un seul mot de passe pour tout (le mot de passe Windows de l'employé)
- Pas besoin de créer des comptes dans ObjectifSMART-AI
- Si un employé quitte la BMCI et son compte AD est désactivé → il perd automatiquement l'accès
- Les rôles (RH/Manager/Collab) viennent directement des groupes AD de la BMCI

**Implémentation Python :**
```python
from ldap3 import Server, Connection, ALL, NTLM, SIMPLE
from ldap3.core.exceptions import LDAPBindError

LDAP_SERVER = "ldap://ad.bmci.co.ma"   # ou l'IP du contrôleur de domaine
LDAP_BASE_DN = "DC=bmci,DC=co,DC=ma"
DOMAIN = "BMCI"

def authenticate_with_ad(username: str, password: str) -> dict | None:
    """
    Authentifie un employé via Active Directory.
    Retourne son profil complet ou None si échec.
    """
    server = Server(LDAP_SERVER, get_info=ALL)
    
    try:
        # Tenter la connexion avec les identifiants de l'employé
        conn = Connection(
            server,
            user=f"{DOMAIN}\\{username}",   # format DOMAIN\username
            password=password,
            authentication=NTLM,
            auto_bind=True
        )
    except LDAPBindError:
        return None  # Identifiants incorrects

    # Rechercher le profil complet de l'employé
    conn.search(
        search_base=LDAP_BASE_DN,
        search_filter=f"(sAMAccountName={username})",
        attributes=[
            'displayName',      # Nom complet
            'mail',             # Email
            'department',       # Département
            'title',            # Titre/poste
            'manager',          # DN du manager
            'memberOf',         # Groupes d'appartenance
            'employeeID'        # Matricule employé
        ]
    )

    if not conn.entries:
        return None

    entry = conn.entries[0]
    groups = [str(g) for g in entry.memberOf.values]

    # Mapper les groupes AD aux rôles ObjectifSMART-AI
    role = map_ad_groups_to_role(groups)

    return {
        "username": username,
        "name": str(entry.displayName),
        "email": str(entry.mail),
        "department": str(entry.department),
        "role": role,
        "groups": groups
    }

def map_ad_groups_to_role(groups: list) -> str:
    """
    Mappe les groupes Active Directory de la BMCI
    aux rôles de ObjectifSMART-AI.
    À ajuster selon les vrais noms de groupes AD de la BMCI.
    """
    groups_upper = [g.upper() for g in groups]
    
    # Adapter ces noms aux vrais groupes AD de la BMCI
    if any("RH" in g or "HR" in g or "RESSOURCES-HUMAINES" in g for g in groups_upper):
        return "HR"
    if any("MANAGER" in g or "RESPONSABLE" in g or "CHEF" in g for g in groups_upper):
        return "MANAGER"
    return "COLLAB"   # Par défaut : collaborateur
```

**Dépendance à installer :**
```bash
pip install ldap3
```

---

### Option B — SSO Windows / Kerberos (recommandée à moyen terme)

**Principe :** Aucune saisie de mot de passe. Quand l'employé ouvre ObjectifSMART-AI dans son navigateur après s'être connecté avec sa carte, l'application reconnaît automatiquement son identité Windows via Kerberos (protocole SSO).

```
Employé insère sa carte → Windows s'ouvre (session Kerberos créée)
        │
        │  Ouvre le navigateur, tape l'URL de ObjectifSMART-AI
        ▼
Navigateur envoie automatiquement le token Kerberos
(header HTTP : Authorization: Negotiate ...)
        │
        ▼
ObjectifSMART-AI valide le token auprès d'AD
→ L'employé est connecté SANS avoir saisi quoi que ce soit
```

**Avantages :**
- Expérience utilisateur parfaite : zéro saisie
- Si la carte est retirée et le PC se verrouille, la session ObjectifSMART-AI expire aussi
- Le plus proche du "insérer la carte → l'app se configure automatiquement"

**Limitation :** Fonctionne uniquement sur le réseau interne de la BMCI (pas en télétravail sans VPN). Nécessite une configuration réseau particulière (SPN, DNS).

**Implémentation :**
```bash
pip install gssapi requests-kerberos
```

```python
# Dans FastAPI, valider le token Kerberos du header HTTP
from gssapi import SecurityContext, Credentials, OID
import base64

def validate_kerberos_token(authorization_header: str) -> dict | None:
    """Valide le token Kerberos envoyé par le navigateur"""
    if not authorization_header.startswith("Negotiate "):
        return None
    
    token = base64.b64decode(authorization_header[10:])
    
    ctx = SecurityContext(usage="accept")
    ctx.step(token)
    
    # Extraire l'identité de l'employé du token validé
    client_name = str(ctx.initiator_name)
    username = client_name.split("@")[0]   # ex: cabid@BMCI.CO.MA → cabid
    
    return get_employee_profile_from_ad(username)
```

---

### Option C — SAML/OIDC via ADFS (recommandée pour production)

**Principe :** La BMCI dispose probablement d'un serveur **ADFS** (Active Directory Federation Services) ou **Azure AD**. Ces serveurs implémentent des protocoles d'identité standards (SAML 2.0, OpenID Connect) utilisés par toutes les grandes applications d'entreprise.

```
Employé clique "Se connecter"
        │
        ▼
ObjectifSMART-AI redirige vers le portail ADFS BMCI
        │
        ▼
ADFS vérifie la session Windows (ou demande la carte)
        │
        ▼
ADFS retourne un token SAML/JWT signé avec :
  - Identité de l'employé
  - Ses groupes et rôles
  - Durée de validité
        │
        ▼
ObjectifSMART-AI valide le token et connecte l'employé
```

**Avantages :**
- Standard industriel (même protocole que Office 365, SAP, etc.)
- Gestion de session centralisée
- Compatible avec l'authentification multi-facteurs (MFA) de la BMCI
- Fonctionne même en télétravail via VPN

**Implémentation :**
```bash
pip install python-saml authlib
```

---

### Option D — Lecture directe de la carte via PC/SC (futur)

**Principe :** Lire directement le numéro unique de la carte (UID) ou le certificat PKI quand elle est insérée, sans passer par Active Directory.

```python
from smartcard.System import readers
from smartcard.util import toHexString

def read_card_uid():
    """Lit l'UID de la carte insérée dans le lecteur"""
    available_readers = readers()
    if not available_readers:
        return None
    
    reader = available_readers[0]
    connection = reader.createConnection()
    connection.connect()
    
    # Commande APDU pour lire l'UID de la carte
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    data, sw1, sw2 = connection.transmit(GET_UID)
    
    return toHexString(data)   # ex: "A1 B2 C3 D4"
```

**Limitation importante :** L'UID seul ne suffit pas — il faut toujours interroger AD pour associer l'UID au profil employé. Cette option est plus complexe et nécessite l'accord de la DSI BMCI pour accéder au système de gestion des cartes.

---

## 6. Recommandation finale

### Pour ObjectifSMART-AI, voici la stratégie recommandée en 3 phases :

```
PHASE 1 — Court terme (1-2 semaines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Implémenter l'Option A (LDAP)
→ L'employé saisit son identifiant BMCI + mot de passe Windows
→ Le rôle est attribué automatiquement depuis AD
→ Plus besoin de comptes séparés dans ObjectifSMART-AI
→ Nécessite : l'adresse IP/DNS du serveur AD de la BMCI
               + un compte de service avec droit de lecture AD

PHASE 2 — Moyen terme (1 mois)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ajouter l'Option B (Kerberos/SSO)
→ Zéro saisie : la carte = connexion automatique
→ Nécessite : configuration réseau (SPN) avec la DSI BMCI

PHASE 3 — Long terme (production)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Basculer sur l'Option C (ADFS/OIDC)
→ Standard bancaire, le plus sécurisé
→ Nécessite : intégration avec la DSI et le service SSO de la BMCI
```

---

## 7. Plan d'implémentation

### Ce qu'il faut demander à la DSI BMCI

Pour implémenter la Phase 1 (LDAP), voici exactement ce dont l'équipe a besoin :

| Information nécessaire | Exemple | Pourquoi |
|------------------------|---------|----------|
| Adresse du serveur AD | `ad.bmci.co.ma` ou `192.168.1.10` | Pour s'y connecter |
| Port LDAP/LDAPS | `389` (LDAP) ou `636` (LDAPS) | Pour la connexion sécurisée |
| Base DN de recherche | `DC=bmci,DC=co,DC=ma` | Pour chercher les employés |
| Noms des groupes AD | `GRP-RH`, `GRP-MANAGERS`, etc. | Pour mapper les rôles |
| Compte de service | Un compte AD en lecture seule | Pour faire les requêtes LDAP |

### Comment tester sans accès à l'AD réel de la BMCI

En attendant l'accès au serveur AD de la BMCI, l'équipe peut tester l'intégration LDAP avec un **Active Directory local de test** en utilisant Docker :

```bash
# Lancer un AD de test local en 1 commande
docker run -d \
  --name ad-test \
  -p 389:389 \
  -p 636:636 \
  -e SAMBA_DOMAIN=BMCI \
  -e SAMBA_REALM=BMCI.CO.MA \
  -e SAMBA_PASSWORD=Admin@1234 \
  nowsci/samba-domain
```

Puis créer des utilisateurs de test qui imitent la structure BMCI :
```python
# Script de peuplement de l'AD de test
from ldap3 import Server, Connection, ALL, MODIFY_ADD

conn = Connection(Server("ldap://localhost:389"), 
                  user="Administrator@BMCI.CO.MA",
                  password="Admin@1234", auto_bind=True)

# Créer un utilisateur RH de test
conn.add("CN=Test RH,OU=Users,DC=bmci,DC=co,DC=ma", 
         attributes={
             "sAMAccountName": "test-rh",
             "mail": "test.rh@bmci.co.ma",
             "department": "Ressources Humaines",
             "memberOf": ["CN=GRP-BMCI-RH,DC=bmci,DC=co,DC=ma"]
         })
```

Cela permet de développer et tester tout le code d'intégration LDAP avant d'avoir accès au vrai AD BMCI.

### Sécurité de l'intégration LDAP — Points d'attention

| Risque | Solution |
|--------|----------|
| LDAP en clair (port 389) | Utiliser **LDAPS (port 636)** avec certificat TLS |
| LDAP injection | Ne jamais construire le filtre LDAP avec des f-strings — utiliser `ldap3` avec échappement automatique |
| Compte de service trop puissant | Créer un compte AD dédié avec **droits de lecture seule uniquement** |
| Mot de passe du compte de service | Le stocker dans `.env`, jamais dans le code source |
| Logs qui exposent les mots de passe | Ne jamais loguer `request.password` ou les identifiants LDAP |

```python
# CORRECT — ldap3 échappe automatiquement les caractères spéciaux
search_filter = f"(sAMAccountName={escape_filter_chars(username)})"

# INCORRECT — vulnérable à l'injection LDAP
search_filter = f"(sAMAccountName={username})"  # ← DANGER
```

### Modifications à apporter à ObjectifSMART-AI

**`server.py`** — Remplacer l'authentification par mot de passe local :
```python
# AVANT (actuel) :
# L'app vérifie le hash bcrypt dans sa propre base SQLite

# APRÈS (avec LDAP) :
# 1. Vérifier les identifiants dans Active Directory BMCI
# 2. Récupérer le profil (nom, email, rôle) depuis AD
# 3. Créer/mettre à jour l'utilisateur localement si nécessaire
# 4. Générer un token de session (comme aujourd'hui)
```

**`Login.tsx`** — Adapter le formulaire :
```typescript
// Remplacer "email@bmci.co.ma" par "Identifiant BMCI (ex: cabid)"
// Le champ email devient un champ "Identifiant réseau"
// Supprimer le select de manager → vient automatiquement d'AD
```

**`requirements.txt`** — Ajouter :
```
ldap3>=2.9.1
```

### Impact sur la base de données SQLite actuelle

Avec l'intégration AD, la base de données locale SQLite ne disparaît pas — elle change de rôle :

```
AVANT (sans AD) :               APRÈS (avec AD) :
SQLite = source de vérité        AD = source de vérité
  → Stocke identifiants           → Authentifie les employés
  → Stocke mots de passe hachés   → Fournit nom, email, rôle, manager
  → Gère les rôles manuellement
                                 SQLite = cache et données métier
                                   → Stocke les objectifs
                                   → Stocke les analyses SMART
                                   → Stocke les sessions (tokens)
                                   → NE stocke plus les mots de passe
```

Quand un employé se connecte via LDAP pour la première fois, on crée une entrée SQLite légère (sans mot de passe) pour stocker ses données métier (objectifs, analyses). Si son compte AD est désactivé, il ne peut plus s'authentifier, même si son entrée SQLite existe encore.

### Exemple de flux complet après intégration LDAP

```
L'employé ouvre ObjectifSMART-AI
        │
        ▼
Saisit : Identifiant BMCI (ex: cabid) + Mot de passe Windows
        │
        ▼
FastAPI interroge AD BMCI via LDAP
        │
        ├─ Authentification échoue → Message d'erreur
        │
        └─ Authentification réussie →
               Nom : Chaimaa ABID
               Email : c.abid@bmci.co.ma
               Département : Ressources Humaines
               Groupe AD : GRP-BMCI-RH
                      │
                      ▼
               Rôle attribué : HR
               Dashboard RH affiché automatiquement
               Manager récupéré depuis AD (pas de select à remplir)
```

---

## Résumé exécutif

Le système de carte de la BMCI est une infrastructure **Smart Card PKI + Active Directory** standard dans les grandes entreprises bancaires. La carte identifie l'employé, Active Directory centralise les droits et le profil.

Pour ObjectifSMART-AI, **il n'est pas nécessaire de lire physiquement la carte**. Il suffit d'interroger Active Directory, qui est la source de vérité de tous les identifiants BMCI. L'intégration LDAP (Option A) est réalisable en 1-2 semaines et résoudrait l'ensemble des vulnérabilités d'authentification identifiées dans notre audit de sécurité.

Le résultat final : un employé BMCI saisit son identifiant réseau habituel, et ObjectifSMART-AI configure automatiquement son espace de travail (Collaborateur, Manager ou RH) sans aucune gestion de compte supplémentaire.

---

*Document produit dans le cadre du Projet Innovation — École Centrale Casablanca 2024-2025*  
*Encadrante : Mme Annoukoubi Maha | Entreprise partenaire : BMCI*
