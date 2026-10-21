# SSO SAML 2.0 — Simulation, migration réelle & retrait

Ce document décrit les **3 états** du SSO et comment passer de l'un à l'autre.
La conception garantit : *simulation pour tester → bascule réelle sans recoder →
retrait trivial pour la prod.*

| État | `SAML_SIMULATION` | SP + IdP configurés | Comportement |
|------|:---:|:---:|--------------|
| **Local** (défaut) | `false` | non | Login email/mot de passe uniquement |
| **Simulation** (dev) | `true` | non | Bouton SSO → page de choix de persona |
| **Réel** (prod) | ignoré | **oui** | Bouton SSO → Entra ID / ADFS |

> Règle d'or : **dès que le SSO réel (SP+IdP) est configuré, la simulation
> s'éteint automatiquement** (`saml_simulation_active = false`). Impossible
> d'avoir les deux en même temps.

---

## 1. Tester en SIMULATION (aucune dépendance, aucun IdP)

1. `backend/.env` → `SAML_SIMULATION=true`
2. Lancer `LANCER_APP.bat`
3. Sur l'écran de login : bouton **« Se connecter avec le SSO BMCI »** →
   choisir une persona (RH / Manager / Collab).

Ce qui est **réellement** exercé : JIT provisioning, mapping groupe→rôle,
session, audit, redirection. Seule la validation de l'assertion XML est simulée.

---

## 2. Migration vers les VRAIES données de l'entreprise

Aucune ligne de code à modifier. 4 étapes :

### a. Installer la dépendance native (une fois)
```bash
pip install -r requirements-saml.txt
```
> ⚠️ `python3-saml` dépend de `xmlsec` (natif). Sous **Windows**, préférer
> **WSL/Docker Linux** (`apt install libxmlsec1-dev`) — sinon l'installation échoue.

### b. Renseigner les secrets dans `backend/.env.local`
`.env.local` est **ignoré par git** et **prioritaire** sur `.env` → c'est là que
vont les vrais secrets (jamais dans `.env` versionné).

```ini
# SP = cette application (déclarée auprès de la DSI)
SAML_SP_ENTITY_ID=https://<url-interne-banque>/api/auth/saml/metadata
SAML_SP_ACS_URL=https://<url-interne-banque>/api/auth/saml/acs

# IdP = annuaire BMCI (valeurs fournies par la DSI)
SAML_IDP_ENTITY_ID=...           # Entity ID / Issuer de l'IdP
SAML_IDP_SSO_URL=...             # URL de connexion SSO
SAML_IDP_X509_CERT=MIID...       # certificat de signature (une seule ligne)

SAML_FRONTEND_REDIRECT=https://<url-interne-banque>
```

### c. Donner les métadonnées SP à la DSI
Démarrer l'app puis transmettre l'URL :
```
https://<url-interne-banque>/api/auth/saml/metadata
```
(XML auto-généré : Entity ID, ACS, certificat éventuel.)

### d. Redémarrer
Au boot, le log affiche `[AUTH] Mode = SSO SAML (reel)`. Le bouton SSO redirige
désormais vers Entra ID / ADFS.

### ⚠️ Spécificité Microsoft Entra ID — claim « groupes »
Par défaut, Entra envoie les groupes en **GUID** (`a1b2-...`), pas `GRP_RH`.
Deux options :
- demander à la DSI d'émettre le claim groupe en **nom** (*Groups assigned to the application*), **ou**
- mettre les **GUID** dans `BANK_GROUP_TO_ROLE` (`backend/app/auth/identity_provider.py`).

Claims configurables si besoin (sinon valeurs Microsoft par défaut) :
`SAML_ATTR_EMAIL`, `SAML_ATTR_NAME`, `SAML_ATTR_GROUPS`.

---

## 3. RETRAIT de la simulation (passage en production propre)

Tout le code de simulation est **isolé dans un seul fichier jetable**.

**Option minimale (suffit) :** s'assurer que `SAML_SIMULATION=false` (défaut).
En prod, dès que le SSO réel est configuré, la simulation est de toute façon
inactive. Le boot logge `*** SIMULATION (DEV) ***` en gros si jamais elle est active.

**Option « suppression totale du code » :**
1. Supprimer `backend/app/controllers/saml_simulation_controller.py`
2. Dans `backend/app/main.py`, retirer les 2 lignes marquées `# [SIMULATION]`
3. (optionnel) Retirer `SAML_SIMULATION` de `backend/.env` et la propriété
   `saml_simulation_active` / le bloc de log dans `config.py` / `main.py`

Aucun autre fichier ne dépend de la simulation → suppression sans effet de bord.

---

## Endpoints SAML (préfixe `/api/auth/saml`)
| Méthode | Route | Rôle |
|--------|-------|------|
| GET | `/status` | `{ enabled, simulation }` (pour le frontend) |
| GET | `/metadata` | Métadonnées SP (XML) pour la DSI |
| GET | `/login` | Démarre le SSO (IdP réel ou page de simulation) |
| POST | `/acs` | Reçoit l'assertion signée, crée la session |
| GET/POST | `/simulate` | **Dev only**, 404 si simulation inactive |
