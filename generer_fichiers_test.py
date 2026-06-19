#!/usr/bin/env python3
"""
generer_fichiers_test.py — (Re)cree les fichiers Excel de DEMO de l'import RH.

POURQUOI CE SCRIPT
    Les .xlsx sont des fichiers BINAIRES. Pour qu'un telechargement « Download ZIP »
    de GitHub ne contienne QUE du texte (rien que certains reseaux d'entreprise
    bloquent), on ne versionne PLUS les .xlsx : on les regenere a la demande, ici,
    a partir de donnees en clair. openpyxl est deja une dependance du projet.

CONTENU
    - fichiers_test/objectifs_collaborateurs_BMCI.xlsx : exemples d'objectifs
      individuels (pour tester l'import RH « objectifs collaborateurs »).
    - fichiers_test/objectifs_strategiques_BMCI.xlsx   : catalogue strategique
      (pour tester l'import « objectifs strategiques »).

USAGE
    python generer_fichiers_test.py
"""

import os
import sys

try:
    from openpyxl import Workbook
except ImportError:
    print("[ERREUR] openpyxl manquant -> pip install -r requirements.txt")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "fichiers_test")

# --- Donnees en clair (versionnees ici, a la place du binaire) ----------------

COLLAB_HEADERS = ["ID", "Collaborateur", "Email", "Titre", "Description",
                  "Entite", "Manager", "Periode", "Contexte"]

COLLAB_ROWS = [
    ["OBJ-001", "Yassine El Amrani", "yassine.elamrani@bmci.ma", "Augmenter le taux d'equipement digital des clients de l'agence de 45% a 65% d'ici le 31 decembre 2026", "Promouvoir l'app mobile BMCI aupres des clients particuliers lors de chaque rendez-vous.", "Reseau Agences", "Khalid Bennani", "2026", "Agence Casablanca Maarif"],
    ["OBJ-002", "Yassine El Amrani", "yassine.elamrani@bmci.ma", "Ameliorer la relation client", "Etre plus a l'ecoute et plus disponible pour les clients.", "Reseau Agences", "Khalid Bennani", "2026", "Agence Casablanca Maarif"],
    ["OBJ-003", "Fatima Zahra Idrissi", "fatima.idrissi@bmci.ma", "Reduire le delai moyen de traitement des dossiers de credit de 8 a 5 jours ouvres avant fin du T3 2026", "Optimiser le circuit d'instruction et de validation des credits entreprises.", "Direction Entreprises", "Nadia Tazi", "T3 2026", "Pole credits PME"],
    ["OBJ-004", "Fatima Zahra Idrissi", "fatima.idrissi@bmci.ma", "Developper le portefeuille PME", "Prospecter de nouvelles entreprises et renforcer les relations existantes.", "Direction Entreprises", "Nadia Tazi", "2026", "Pole credits PME"],
    ["OBJ-005", "Omar Benjelloun", "omar.benjelloun@bmci.ma", "Ouvrir 50 nouveaux comptes professionnels par trimestre tout au long de 2026", "Conquete de la clientele professionnelle et artisans.", "Reseau Agences", "Khalid Bennani", "2026", "Agence Rabat Agdal"],
    ["OBJ-006", "Omar Benjelloun", "omar.benjelloun@bmci.ma", "Monter en competence sur les nouveaux produits", "Mieux connaitre l'offre pour mieux conseiller.", "Reseau Agences", "Khalid Bennani", "T1 2026", "Agence Rabat Agdal"],
    ["OBJ-007", "Salma Cherkaoui", "salma.cherkaoui@bmci.ma", "Porter le score de conformite de l'equipe de 75% a 95% et obtenir la certification AMF d'ici juin 2026", "Renforcer la conformite reglementaire et la lutte anti-blanchiment.", "Direction Conformite", "Rachid Alaoui", "S1 2026", "Pole LCB-FT"],
    ["OBJ-008", "Salma Cherkaoui", "salma.cherkaoui@bmci.ma", "Ameliorer la qualite des controles", "Realiser des controles plus reguliers et mieux documentes.", "Direction Conformite", "Rachid Alaoui", "2026", "Pole LCB-FT"],
    ["OBJ-009", "Mehdi Tahiri", "mehdi.tahiri@bmci.ma", "Migrer 100% des serveurs critiques vers le nouveau datacenter securise avant le 30 septembre 2026", "Projet d'infrastructure pour la resilience et la cybersecurite.", "DSI", "Samir Ouazzani", "T3 2026", "Programme Resilience IT"],
    ["OBJ-010", "Mehdi Tahiri", "mehdi.tahiri@bmci.ma", "Reduire les incidents de securite", "Ameliorer la surveillance et la reactivite face aux menaces.", "DSI", "Samir Ouazzani", "2026", "Programme Resilience IT"],
]

STRAT_HEADERS = ["ID", "Titre", "Description", "Direction", "Priorite"]

STRAT_ROWS = [
    ["STRAT-01", "Accelerer la transformation digitale", "Digitaliser 80% des parcours clients et atteindre 1 million d'utilisateurs actifs de l'app mobile d'ici fin 2026.", "Direction Digitale", 1],
    ["STRAT-02", "Ameliorer la satisfaction client", "Atteindre un NPS de 60 et reduire le taux de reclamation de 25% avant decembre 2026.", "Direction Clientele", 1],
    ["STRAT-03", "Renforcer la maitrise des risques", "Maintenir le cout du risque sous 0,5% des encours et reduire les creances en souffrance de 15% en 2026.", "Direction des Risques", 1],
    ["STRAT-04", "Developper le financement des PME", "Augmenter de 15% l'encours de credit aux PME et financer 500 nouvelles entreprises en 2026.", "Direction Entreprises", 2],
    ["STRAT-05", "Promouvoir la finance durable (ESG)", "Financer 2 milliards MAD de projets verts d'ici 2027 et publier un rapport ESG annuel.", "Direction RSE", 2],
    ["STRAT-06", "Optimiser l'efficacite operationnelle", "Reduire le coefficient d'exploitation a 50% d'ici fin 2026 par l'automatisation des processus.", "Direction Financiere", 2],
    ["STRAT-07", "Renforcer la cybersecurite", "Atteindre 100% de conformite aux normes Bank Al-Maghrib et reduire les incidents de securite de 40% en 2026.", "DSI", 1],
    ["STRAT-08", "Developper les talents et l'engagement", "Former 100% des collaborateurs aux competences digitales et porter le taux d'engagement a 80% d'ici fin 2026.", "DRH", 3],
]


def write_xlsx(path: str, sheet: str, headers: list, rows: list) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(path)
    print(f"  [OK] {os.path.relpath(path, HERE)}  ({len(rows)} lignes)")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Generation des fichiers Excel de demo (import RH) :")
    write_xlsx(os.path.join(OUT_DIR, "objectifs_collaborateurs_BMCI.xlsx"),
               "Objectifs", COLLAB_HEADERS, COLLAB_ROWS)
    write_xlsx(os.path.join(OUT_DIR, "objectifs_strategiques_BMCI.xlsx"),
               "Strategie", STRAT_HEADERS, STRAT_ROWS)
    print("Termine. Ces fichiers servent a tester l'import Excel cote RH.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
