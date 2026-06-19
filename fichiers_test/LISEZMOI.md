# Fichiers de test (import Excel RH)

Ce dossier contient des **fichiers Excel d'exemple** pour tester l'import RH
(objectifs collaborateurs + objectifs stratégiques).

## ⚠️ Les `.xlsx` ne sont pas versionnés

Les `.xlsx` sont des fichiers **binaires**. Pour que le téléchargement
« Download ZIP » de GitHub ne contienne **que du texte** (certains réseaux
d'entreprise bloquent les binaires), on ne les commite pas : on les **régénère**.

## Régénérer les fichiers

À la racine du projet :

```bash
python generer_fichiers_test.py
```

Cela (re)crée :

- `objectifs_collaborateurs_BMCI.xlsx` — 10 objectifs individuels d'exemple
- `objectifs_strategiques_BMCI.xlsx` — 8 axes stratégiques d'exemple

> Nécessite `openpyxl` (déjà dans `requirements.txt`).
