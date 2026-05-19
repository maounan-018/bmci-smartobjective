# Authentification ObjectifSMART-AI — Solution proposée et Questions DSI
## Document de cadrage pour la réunion avec la Direction des Systèmes d'Information

**Préparé par :** Groupe 03 — École Centrale Casablanca 2024-2025  
**À l'attention de :** DSI BMCI — ABID Chaimaa, ESSAEGH Keltoum  
**Encadrante :** Mme Annoukoubi Maha  
**Objet :** Amélioration du système d'authentification de ObjectifSMART-AI

---

## 1. Observations de terrain

Dans le cadre de notre projet, nous avons eu l'opportunité d'observer le fonctionnement quotidien des équipes BMCI. Ces observations constituent le point de départ de notre réflexion.

### Ce que nous avons constaté

**Sur l'usage de la carte :**
- Certains employés utilisent une **carte personnelle pour démarrer leur poste de travail**
- Lorsque cette carte est retirée, le PC **se verrouille automatiquement**
- La même carte sert également à **badger aux entrées et sorties** des locaux
- Cependant, nous avons remarqué que **tous les employés ne semblent pas utiliser cette carte pour travailler sur leur ordinateur** — certains postes semblent fonctionner sans insertion de carte

**Sur les logiciels et les droits :**
- Les logiciels installés sur les postes semblent **déjà configurés selon l'identité de l'employé** connecté
- Certains employés peuvent installer des programmes ou des bibliothèques, d'autres non — ces **droits semblent liés à leur fonction** dans l'entreprise
- Ce comportement suggère qu'il existe un **système central** qui connaît l'identité, la fonction et les droits de chaque employé

**Sur l'authentification actuelle de ObjectifSMART-AI :**
- Dans sa version actuelle, notre application gère ses propres comptes utilisateurs
- L'employé doit créer un compte séparé avec un mot de passe distinct
- Il doit manuellement indiquer son rôle (Collaborateur, Manager ou RH) et sélectionner son manager
- Ce fonctionnement est **déconnecté du système d'identité existant de la BMCI**
- Il crée des **vulnérabilités** : mots de passe faibles possibles, comptes non révoqués au départ d'un employé, erreurs de rôle ou de manager

---

## 2. Notre hypothèse de travail

À partir de ces observations, nous formulons l'hypothèse suivante :

> La BMCI dispose d'un **système centralisé de gestion des identités** qui contient les informations de tous les employés (nom, fonction, département, hiérarchie, droits). La carte d'accès est l'un des moyens d'authentification auprès de ce système, mais **elle n'est probablement pas utilisée par tous les employés sur tous les postes**.

Si cette hypothèse est correcte, ce système centralisé représente exactement la source de données dont ObjectifSMART-AI a besoin pour configurer automatiquement l'espace de travail de chaque employé.

---

## 3. La solution que nous proposons

### Principe général

Notre idée repose sur un constat simple : **la règle d'or de la sécurité reste la vérification des identifiants de l'employé dans la base de données BMCI**. Peu importe le moyen utilisé pour s'authentifier, c'est toujours cette vérification qui donne accès à l'application.

La carte d'accès, dans notre vision, ne remplace pas cette vérification — **elle l'automatise**. Elle lit les identifiants de l'employé et les envoie automatiquement au système d'authentification, sans que l'employé ait besoin de les saisir manuellement.

### Les deux cas d'utilisation

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  CAS 1 — L'employé utilise sa carte sur son poste de travail        │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Carte insérée → Windows lit les identifiants de la carte           │
│        │                                                            │
│        ▼                                                            │
│  ObjectifSMART-AI récupère automatiquement l'identité Windows       │
│  (sans que l'employé saisisse quoi que ce soit)                     │
│        │                                                            │
│        ▼                                                            │
│  Vérification dans la base de données BMCI                          │
│        │                                                            │
│        ▼                                                            │
│  Second facteur d'authentification (MFA)                            │
│        │                                                            │
│        ▼                                                            │
│  Espace ObjectifSMART-AI configuré automatiquement                  │
│  (rôle, manager, équipe — tout vient de la base BMCI)               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  CAS 2 — L'employé n'utilise pas de carte                           │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  L'employé ouvre ObjectifSMART-AI dans son navigateur               │
│        │                                                            │
│        ▼                                                            │
│  Il saisit son identifiant BMCI + son mot de passe                  │
│  (les mêmes qu'il utilise pour ses autres outils BMCI)              │
│        │                                                            │
│        ▼                                                            │
│  Vérification dans la base de données BMCI                          │
│        │                                                            │
│        ▼                                                            │
│  Second facteur d'authentification (MFA)                            │
│        │                                                            │
│        ▼                                                            │
│  Espace ObjectifSMART-AI configuré automatiquement                  │
│  (rôle, manager, équipe — tout vient de la base BMCI)               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Pourquoi le double facteur d'authentification (MFA) est indispensable

Même avec ce système, deux risques subsistent :
- Quelqu'un pourrait **trouver ou voler la carte** d'un employé
- Quelqu'un pourrait **connaître les identifiants** d'un employé (mot de passe partagé, phishing, etc.)

Le MFA (authentification multi-facteurs) ajoute une couche de sécurité supplémentaire : même si quelqu'un possède la carte ou les identifiants, il lui faudra également **valider un second facteur** (code envoyé sur le téléphone professionnel, application d'authentification, etc.) pour accéder à l'application.

```
Identifiants corrects (carte OU saisie manuelle)
        │
        ▼
Second facteur requis :
  - Code envoyé par SMS sur le téléphone professionnel de l'employé
  - Notification sur une application mobile (Microsoft Authenticator...)
  - Code sur l'email professionnel BMCI
        │
        ▼
Accès accordé uniquement si les deux facteurs sont validés
```

### Ce que cette solution change concrètement pour l'employé

| Situation | Avant (version actuelle) | Après (solution proposée) |
|---|---|---|
| Première utilisation | Créer un compte, choisir son rôle, sélectionner son manager | Aucune inscription — l'app se configure seule |
| Connexion avec carte | Impossible de détecter la carte | Connexion automatique dès l'ouverture |
| Connexion sans carte | Identifiant + mot de passe créés pour l'app | Identifiant + mot de passe BMCI habituels |
| Changement de poste | Doit modifier son profil manuellement | Mis à jour automatiquement depuis la base BMCI |
| Départ de la BMCI | Compte reste actif jusqu'à suppression manuelle | Accès révoqué automatiquement |

---

## 4. Ce que nous devons vérifier et comprendre

Pour savoir si cette solution est réalisable, nous avons besoin de réponses à plusieurs questions. Elles sont organisées du plus général au plus spécifique.

---

### Thème A — Vérifier notre compréhension du système existant

**A1.** Nous avons observé que certains employés utilisent une carte pour démarrer leur PC. Est-ce le cas de tous les employés de bureau, ou seulement d'une partie d'entre eux ? Y a-t-il des catégories de postes qui fonctionnent sans carte ?

**A2.** Indépendamment de la carte, existe-t-il un **identifiant réseau unique** attribué à chaque employé BMCI (un nom d'utilisateur et un mot de passe) pour accéder aux systèmes informatiques ? Est-ce que tous les employés en possèdent un ?

**A3.** Cet identifiant réseau est-il le même pour accéder à tous les outils internes (messagerie, intranet, applications métiers) ? Ou chaque application a-t-elle ses propres identifiants ?

**A4.** Existe-t-il une base de données centrale qui contient les informations de tous les employés — nom, département, fonction, manager hiérarchique — et qui est maintenue à jour en temps réel par la RH ou la DSI ?

---

### Thème B — Comprendre la relation entre la carte et le système d'identité

**B1.** Lorsqu'un employé insère sa carte dans le PC, que se passe-t-il exactement du côté du système d'information ? La carte envoie-t-elle les identifiants de l'employé au système central, ou fonctionne-t-elle de manière indépendante ?

**B2.** Notre hypothèse est que la carte "lit et transmet automatiquement" les identifiants de l'employé, évitant ainsi la saisie manuelle. Est-ce une bonne compréhension du fonctionnement ?

**B3.** Si un employé perd sa carte, peut-il quand même accéder à ses outils informatiques en saisissant manuellement ses identifiants ? Ou la carte est-elle l'unique moyen de connexion ?

---

### Thème C — Faisabilité de notre solution

**C1.** Serait-il techniquement possible pour une application web interne comme ObjectifSMART-AI de **vérifier les identifiants d'un employé** directement dans votre système central, plutôt que de gérer sa propre base d'utilisateurs ?

**C2.** Dans le cas où un employé est connecté à son poste via sa carte, serait-il possible pour notre application de **récupérer automatiquement son identité** sans lui demander de se reconnecter ?

**C3.** La BMCI dispose-t-elle déjà d'un système d'**authentification multi-facteurs** (envoi d'un code par SMS, application d'authentification, etc.) pour ses outils internes ? Si oui, serait-il possible de le réutiliser pour notre application ?

**C4.** D'autres applications internes à la BMCI fonctionnent-elles déjà sur ce principe — c'est-à-dire en utilisant les identifiants BMCI existants plutôt que leurs propres comptes ? Si oui, lesquelles, et comment ont-elles été intégrées ?

---

### Thème D — Informations organisationnelles nécessaires

**D1.** Comment les rôles et responsabilités des employés sont-ils structurés dans votre système ? Existe-t-il des catégories ou des groupes qui distinguent, par exemple, les collaborateurs de terrain, les managers et les équipes RH ?

**D2.** La relation hiérarchique entre un collaborateur et son manager direct est-elle enregistrée dans votre système ? Est-elle maintenue à jour automatiquement lors des changements d'équipe ?

**D3.** Quand un employé change de poste ou rejoint un nouveau département, dans quel délai cette information est-elle répercutée dans vos systèmes d'information ?

---

### Thème E — Cadre et prochaines étapes

**E1.** Si nous souhaitons avancer dans cette direction, y a-t-il une procédure formelle à suivre pour qu'une application obtienne le droit de s'interfacer avec le système d'identité de la BMCI ?

**E2.** Existe-t-il des contraintes de sécurité, de confidentialité ou réglementaires que nous devons prendre en compte avant de poursuivre dans cette voie ?

**E3.** Avec qui au sein de la DSI devrions-nous travailler pour progresser techniquement sur ce sujet ?

---

## 5. Ce que nous attendons de cette réunion

À l'issue de cet échange, nous espérons avoir des réponses à ces quatre questions essentielles :

**1.** Est-ce que tous les employés BMCI disposent d'un identifiant réseau unique, avec ou sans carte ?

**2.** Est-il possible pour ObjectifSMART-AI de vérifier ces identifiants dans votre système central plutôt que de gérer les siens propres ?

**3.** La BMCI dispose-t-elle d'un système MFA que nous pourrions réutiliser, ou devrons-nous en construire un ?

**4.** Quelles sont les étapes concrètes et les interlocuteurs pour avancer sur cette intégration ?

---

*Document préparé par Groupe 03 — École Centrale Casablanca 2024-2025*
*Encadrante : Mme Annoukoubi Maha | Entreprise partenaire : BMCI*
*ABID Chaimaa, ESSAEGH Keltoum*
