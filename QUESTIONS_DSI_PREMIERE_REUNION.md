# Questions pour la DSI BMCI — Première Réunion
## Comprendre le système d'identité et d'authentification

**Contexte :** L'équipe Groupe 03 a développé ObjectifSMART-AI, un outil d'analyse d'objectifs SMART pour la BMCI. Dans sa version actuelle, l'application gère ses propres comptes utilisateurs (inscription, mot de passe, rôle). Nous avons observé que la BMCI dispose déjà d'un système d'identité sophistiqué et souhaitons comprendre comment il fonctionne pour envisager une meilleure intégration.

---

## Observations de l'équipe

Avant de poser nos questions, voici ce que nous avons pu observer lors de notre présence à la BMCI :

- Chaque employé possède une **carte personnelle** utilisée pour démarrer son poste de travail
- Lorsque la carte est retirée, le PC **se verrouille automatiquement**
- Cette même carte sert à **badger à l'entrée et à la sortie** des locaux
- Une fois connecté avec la carte, les **logiciels semblent déjà configurés** avec l'identité de l'employé
- Certains employés peuvent installer des logiciels ou des bibliothèques, d'autres non — ces **droits semblent liés à la fonction** de l'employé

À partir de ces observations, nous avons formulé des hypothèses que nous souhaiterions vérifier avec vous.

---

## Questions — De l'observation à la compréhension

### Partie 1 — Comprendre le système de carte

**Q1.** Nous avons remarqué que chaque employé utilise une carte pour démarrer son poste de travail. Pouvez-vous nous expliquer, dans les grandes lignes, comment fonctionne ce système ? Est-ce un système propre à la BMCI ou un standard bancaire ?

**Q2.** La même carte sert à la fois pour le poste de travail et pour les accès physiques (portes, badgeage). Ces deux usages sont-ils gérés par le même système, ou par des systèmes distincts qui communiquent entre eux ?

**Q3.** Lorsqu'un employé insère sa carte et ouvre une session sur son PC, que se passe-t-il concrètement "derrière" ? Y a-t-il une vérification auprès d'un serveur central ? Ou tout est contenu dans la carte elle-même ?

---

### Partie 2 — Comprendre la gestion des identités et des droits

**Q4.** Nous avons observé que certains employés peuvent installer des programmes ou des bibliothèques sur leur PC, et d'autres non. Comment ces droits sont-ils définis et attribués ? Est-ce lié à la fonction, au département, ou à autre chose ?

**Q5.** Existe-t-il un système central à la BMCI qui gère l'ensemble des identités des employés — c'est-à-dire qui stocke les informations sur chaque employé (nom, département, fonction, manager, droits) ? Si oui, comment s'appelle-t-il et qui en est responsable ?

**Q6.** Quand un employé change de poste ou de département, comment ses droits et ses accès sont-ils mis à jour ? C'est un processus automatique ou manuel ?

**Q7.** Quand un employé quitte la BMCI, comment son accès à l'ensemble des systèmes est-il révoqué ? Y a-t-il un processus centralisé ou chaque application gère-t-elle cela indépendamment ?

---

### Partie 3 — Comprendre comment les autres applications intègrent ce système

**Q8.** Les autres logiciels internes de la BMCI (outils métiers, intranet, applications RH) utilisent-ils le même système d'authentification que le poste de travail ? L'employé se connecte-t-il avec les mêmes identifiants partout ?

**Q9.** Avez-vous déjà intégré une application développée par une équipe interne ou externe à votre système d'authentification existant ? Si oui, comment cela s'est-il passé ? Quelles étapes ont été nécessaires ?

**Q10.** Existe-t-il une documentation, un guide, ou une procédure standard pour qu'une nouvelle application puisse utiliser le système d'identité de la BMCI plutôt que de créer ses propres comptes ?

---

### Partie 4 — Notre problème et nos hypothèses

**Q11.** Dans la version actuelle d'ObjectifSMART-AI, chaque utilisateur doit créer un compte séparé avec un nouveau mot de passe. Nous avons l'intuition que ce n'est pas idéal pour un environnement bancaire et qu'il serait préférable que l'application reconnaisse directement un employé BMCI dès qu'il s'y connecte. Est-ce quelque chose de faisable techniquement dans votre infrastructure ?

**Q12.** Notre hypothèse est que si un employé est déjà identifié sur son poste de travail via sa carte, il devrait être possible pour une application web interne de récupérer automatiquement son identité sans lui demander de se reconnecter. Cette hypothèse est-elle correcte ? Est-ce quelque chose qui se fait déjà pour d'autres applications ?

**Q13.** Nous pensons également que les informations dont nous avons besoin — nom de l'employé, son département, sa fonction (collaborateur, manager ou RH), et son manager direct — sont déjà disponibles quelque part dans vos systèmes. Est-ce exact ? Si oui, est-il possible d'y accéder depuis notre application ?

---

### Partie 5 — Faisabilité et prochaines étapes

**Q14.** Si nous souhaitons progresser dans cette direction — c'est-à-dire faire en sorte qu'ObjectifSMART-AI utilise directement le système d'identité de la BMCI — avec qui devrions-nous collaborer au sein de la DSI ? Y a-t-il une équipe spécialisée dans ce domaine ?

**Q15.** Y a-t-il des contraintes réglementaires, de sécurité ou de gouvernance que nous devons connaître avant d'aller plus loin dans cette intégration ?

---

## Ce que nous espérons comprendre à l'issue de cette réunion

À la fin de cet échange, nous aimerions avoir des réponses à ces trois questions fondamentales :

1. **Comment fonctionne le système d'identité de la BMCI** — pour confirmer ou corriger nos hypothèses
2. **Est-ce qu'une intégration est techniquement possible** — et si oui, à quel niveau
3. **Qui contacter et quelles sont les étapes suivantes** — pour progresser dans la bonne direction

---

*Document préparé par Groupe 03 — École Centrale Casablanca 2024-2025*
*Encadrante : Mme Annoukoubi Maha | Entreprise partenaire : BMCI*
