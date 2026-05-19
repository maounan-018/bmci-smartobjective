# Intégration Active Directory — Architecture et Questions DSI
## ObjectifSMART-AI × BMCI

**Contexte :** Suite à l'analyse du système de carte BMCI, l'équipe envisage de faire d'Active Directory (AD) la source de vérité pour l'authentification et la configuration automatique des utilisateurs dans ObjectifSMART-AI.

---

## 1. Ce que tu as bien compris — Synthèse des options

### Option A vs Option B : la vraie différence

Tu as raison. La différence fondamentale entre A et B n'est pas la sécurité, c'est l'**expérience utilisateur** :

| | Option A (LDAP) | Option B (Kerberos/SSO) |
|---|---|---|
| **Ce que fait l'employé** | Saisit son identifiant BMCI + mot de passe Windows | N'entre rien — il insère juste sa carte |
| **Comment ça marche** | L'app vérifie les identifiants dans AD | Windows a déjà une session active, l'app la réutilise |
| **Innovation apportée** | Un seul mot de passe pour tout | Zéro friction — la carte = la connexion |
| **Analogie** | Comme se connecter à Gmail avec son compte Google | Comme déverrouiller son iPhone avec Face ID — automatique |

**Option C (SAML/ADFS) :** Tu as aussi raison, ce n'est pas une innovation visible pour l'utilisateur. C'est une amélioration d'infrastructure — plus robuste, plus conforme aux standards bancaires, mieux intégrée avec les audits de sécurité. C'est une décision technique, pas fonctionnelle.

---

## 2. L'impact sur l'architecture — Ce qui change vraiment

Tu as mis le doigt sur le point le plus important. Voici exactement comment l'architecture doit évoluer.

### Architecture actuelle (manuelle)

```
Inscription d'un collaborateur :
  1. L'employé choisit son rôle (Collab / Manager / RH)
  2. Il sélectionne son manager dans une liste
  3. Il crée son mot de passe
  4. Toutes ces infos sont stockées dans SQLite
  
Problèmes :
  → Erreurs de saisie (mauvais manager sélectionné)
  → Si un employé change de poste, son profil n'est pas mis à jour
  → Comptes orphelins si un employé quitte la BMCI
  → La BMCI doit gérer DEUX systèmes d'identité (AD + ObjectifSMART)
```

### Architecture cible (pilotée par AD)

```
Première connexion d'un collaborateur :
  1. L'employé saisit son identifiant réseau BMCI (ou insère sa carte)
  2. AD répond : "Voici qui il est, son rôle, son manager, son département"
  3. ObjectifSMART crée automatiquement son profil
  4. L'employé arrive directement sur son dashboard configuré

Connexions suivantes :
  1. Même processus — AD est consulté à chaque connexion
  2. Si son rôle a changé dans AD → ObjectifSMART se met à jour automatiquement
  3. Si son compte AD est désactivé → il ne peut plus se connecter
```

### Ce qui doit changer dans le code

**Suppression du formulaire d'inscription manuel :**
```
AVANT : Page "S'inscrire" avec champs nom/email/mot de passe/manager/rôle
APRÈS : Aucune inscription — tout vient d'AD à la première connexion
```

**La table `users` dans SQLite change de rôle :**
```sql
-- AVANT : stocke tout, y compris les mots de passe
CREATE TABLE users (
    id, email, password_hash, name, role, manager_id, team, entity
);

-- APRÈS : cache léger, pas de mot de passe
CREATE TABLE users (
    id,
    ad_username,        -- identifiant réseau BMCI (cabid)
    email,              -- depuis AD
    name,               -- depuis AD
    role,               -- depuis AD (déduit des groupes)
    manager_ad_username,-- depuis l'attribut manager d'AD
    department,         -- depuis AD
    last_ad_sync,       -- dernière synchronisation avec AD
    -- PLUS DE password_hash
);
```

**Nouveau flux de connexion :**
```python
@app.post("/api/auth/login")
def login(body: LoginRequest):
    # 1. Authentifier via AD
    ad_profile = authenticate_with_ad(body.username, body.password)
    if not ad_profile:
        raise HTTPException(401, "Identifiants incorrects")

    # 2. Créer ou mettre à jour l'utilisateur dans SQLite
    user = sync_user_from_ad(ad_profile)
    # → Si l'employé n'existe pas en base : création automatique
    # → Si son rôle a changé dans AD : mise à jour automatique

    # 3. Créer une session
    token = generate_token()
    return {"token": token, "user": user}

def sync_user_from_ad(ad_profile: dict) -> dict:
    """
    Crée ou met à jour l'utilisateur local à partir des données AD.
    C'est le cœur de la synchronisation.
    """
    with db_session() as conn:
        existing = conn.execute(
            "SELECT * FROM users WHERE ad_username = ?",
            (ad_profile["username"],)
        ).fetchone()

        if not existing:
            # Première connexion → création automatique
            conn.execute('''
                INSERT INTO users (id, ad_username, email, name, role,
                                   manager_ad_username, department, last_ad_sync)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"user-{secrets.token_hex(4)}",
                ad_profile["username"],
                ad_profile["email"],
                ad_profile["name"],
                ad_profile["role"],          # déduit des groupes AD
                ad_profile["manager"],       # attribut manager d'AD
                ad_profile["department"],
                datetime.now().isoformat()
            ))
        else:
            # Connexion suivante → mise à jour si changement
            conn.execute('''
                UPDATE users SET
                    role = ?, manager_ad_username = ?,
                    department = ?, last_ad_sync = ?
                WHERE ad_username = ?
            ''', (
                ad_profile["role"],
                ad_profile["manager"],
                ad_profile["department"],
                datetime.now().isoformat(),
                ad_profile["username"]
            ))
```

---

## 3. Ce qu'il faut savoir avant de démarrer

Pour mettre en place cette intégration, l'équipe a besoin de deux types d'informations : **techniques** (pour coder) et **organisationnelles** (pour comprendre la structure BMCI).

### 3.1 Informations techniques indispensables

| Information | Exemple attendu | Pour quoi faire |
|---|---|---|
| Adresse du serveur AD | `ad01.bmci.co.ma` ou `192.168.10.5` | Se connecter au bon serveur |
| Port LDAP | `389` (non chiffré) ou `636` (LDAPS chiffré) | Ouvrir la bonne connexion |
| Nom de domaine | `BMCI` ou `bmci.co.ma` | Format `DOMAINE\username` |
| Base de recherche (Base DN) | `DC=bmci,DC=co,DC=ma` | Savoir où chercher les employés |
| Compte de service | `svc-smartobjective` | Compte dédié pour nos requêtes LDAP |
| Mot de passe du compte de service | À stocker dans `.env` | S'authentifier pour lire l'AD |

### 3.2 Informations sur la structure de l'AD

| Information | Exemple attendu | Pour quoi faire |
|---|---|---|
| Noms des groupes RH | `GRP-BMCI-RH` ou `CN=RH-Team,...` | Attribuer le rôle HR |
| Noms des groupes Managers | `GRP-BMCI-MANAGERS` | Attribuer le rôle MANAGER |
| Noms des groupes Collaborateurs | `GRP-BMCI-EMPLOYES` | Attribuer le rôle COLLAB |
| Attribut du nom complet | `displayName` (standard) | Afficher le nom dans l'app |
| Attribut email | `mail` (standard) | Email de l'employé |
| Attribut département | `department` (standard) | Filtrage par entité |
| Attribut manager | `manager` (standard) | Lier collab ↔ manager automatiquement |
| Attribut matricule | `employeeID` ou `employeeNumber` | Identifiant unique RH |

---

## 4. Questions à poser à la DSI BMCI

Voici les questions organisées par thème, prêtes à être posées lors d'une réunion avec la DSI.

---

### Thème 1 — Accès technique à l'Active Directory

> **Question 1.1**
> Pouvez-vous nous fournir l'adresse IP ou le nom DNS du contrôleur de domaine Active Directory accessible depuis le réseau où sera déployée notre application ?

> **Question 1.2**
> Le protocole LDAP (port 389) ou LDAPS chiffré (port 636) est-il disponible ? Recommandez-vous l'un ou l'autre pour une application interne ?

> **Question 1.3**
> Pouvez-vous créer un **compte de service dédié** (ex: `svc-smartobjective`) avec des droits de **lecture seule** sur l'annuaire ? Ce compte ne pourra que lire les données, jamais les modifier.

> **Question 1.4**
> Y a-t-il un environnement de **test ou de recette** de l'Active Directory disponible pour que notre équipe puisse développer et tester sans toucher à l'AD de production ?

---

### Thème 2 — Structure des données employés dans AD

> **Question 2.1**
> Quels sont les **noms exacts des groupes Active Directory** qui distinguent les collaborateurs, les managers et les équipes RH ? (ex: `GRP-RH`, `GRP-MANAGERS`, etc.)

> **Question 2.2**
> L'attribut `manager` est-il **systématiquement renseigné** pour tous les employés ? Est-il maintenu à jour lors des changements hiérarchiques ?

> **Question 2.3**
> Quels attributs AD contiennent les informations suivantes ?
> - Le nom complet de l'employé
> - Son adresse email professionnelle
> - Son département / entité (Direction Digitale, Direction Finance, etc.)
> - Son titre / poste
> - Son matricule RH

> **Question 2.4**
> La structure organisationnelle est-elle représentée dans les **OU (Unités d'Organisation)** de l'AD ? Par exemple : `OU=Direction_Digitale,OU=BMCI,...` ?

---

### Thème 3 — Gestion du cycle de vie des employés

> **Question 3.1**
> Quand un employé **change de poste ou de département**, dans quel délai son compte AD est-il mis à jour ? Qui est responsable de cette mise à jour (RH, DSI, manager) ?

> **Question 3.2**
> Quand un employé **quitte la BMCI**, quel est le processus de désactivation de son compte AD ? Est-ce automatique (lié au SIRH) ou manuel ?
> *(Note : Si son compte AD est désactivé, il perd automatiquement l'accès à ObjectifSMART-AI — ce qui est exactement le comportement souhaité.)*

> **Question 3.3**
> Existe-t-il des employés qui ont **plusieurs rôles simultanément** (ex: un manager qui est aussi collaborateur dans un autre projet) ? Comment cela est-il représenté dans AD ?

---

### Thème 4 — Gouvernance et sécurité

> **Question 4.1**
> Y a-t-il des **restrictions réseau** (firewall, VLAN) sur l'accès au serveur LDAP ? Notre serveur applicatif sera-t-il autorisé à y accéder ?

> **Question 4.2**
> Existe-t-il une politique de **confidentialité des données AD** qui limiterait les attributs que nous pouvons lire ? Par exemple, est-ce que l'attribut `manager` est public pour toutes les applications internes ?

> **Question 4.3**
> Des applications internes BMCI **utilisent-elles déjà AD pour l'authentification** ? Pouvez-vous nous orienter vers les équipes qui les ont développées pour s'inspirer de leur approche ?

> **Question 4.4**
> La BMCI dispose-t-elle d'un serveur **ADFS (Active Directory Federation Services)** ou d'**Azure AD Connect** ? Cela nous permettrait d'utiliser des protocoles modernes (OIDC/SAML) à terme.

---

### Thème 5 — Synchronisation et mise à jour en temps réel

> **Question 5.1**
> Existe-t-il un mécanisme de **notification en temps réel** quand un compte AD est modifié (changement de groupe, désactivation) ? Ou devons-nous interroger AD à chaque connexion de l'employé ?

> **Question 5.2**
> En cas de **changement de manager** pour un collaborateur, à quel moment ce changement est-il visible dans l'AD ? (Immédiatement, dans les 24h, dans la semaine ?)

> **Question 5.3**
> Y a-t-il des **plages de maintenance** de l'AD pendant lesquelles il pourrait être indisponible ? Comment notre application devrait-elle se comporter pendant ces plages ?

---

## 5. Ce que l'intégration AD apporte réellement à ObjectifSMART-AI

Au-delà de la sécurité, voici les vrais gains fonctionnels pour chaque partie prenante :

### Pour les collaborateurs
- ✅ Zéro inscription — première connexion = compte automatiquement créé
- ✅ Pas de sélection du manager — récupéré depuis AD
- ✅ Si mutation vers une autre entité → dashboard mis à jour automatiquement

### Pour les managers
- ✅ Leur équipe dans ObjectifSMART-AI = leur équipe réelle dans AD
- ✅ Quand un nouveau collaborateur rejoint leur équipe dans AD → il apparaît automatiquement dans leur dashboard
- ✅ Quand un collaborateur les quitte dans AD → il disparaît de leur vue

### Pour la RH (BMCI)
- ✅ Un seul référentiel : AD. Plus besoin de gérer les comptes dans ObjectifSMART-AI
- ✅ Départ d'employé = désactivation AD = accès révoqué automatiquement
- ✅ Conformité RGPD facilitée : une seule source de données employés

### Pour la DSI BMCI
- ✅ Audit simplifié : tous les accès à ObjectifSMART-AI tracés dans les logs AD
- ✅ Pas de nouvelle base de mots de passe à sécuriser
- ✅ Conforme aux exigences de la Direction Générale sur la centralisation des identités

---

## 6. Résumé — Ce qu'il faut absolument obtenir pour démarrer

Par ordre de priorité :

```
PRIORITÉ 1 — Sans ça, impossible de commencer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Adresse du serveur AD (IP ou DNS)
□ Nom de domaine BMCI
□ Compte de service lecture seule + mot de passe
□ Accès réseau confirmé depuis notre serveur applicatif

PRIORITÉ 2 — Pour configurer les rôles correctement
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Noms exacts des groupes AD (RH, Managers, Collaborateurs)
□ Confirmation que l'attribut `manager` est bien renseigné
□ Attributs disponibles (displayName, mail, department, etc.)

PRIORITÉ 3 — Pour une intégration robuste
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Environnement AD de test disponible
□ Processus de désactivation des comptes (délais)
□ Contraintes réseau/firewall éventuelles
```

---

*Document préparé par Groupe 03 — École Centrale Casablanca 2024-2025*
*Encadrante : Mme Annoukoubi Maha | Entreprise partenaire : BMCI*
