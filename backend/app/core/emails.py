#!/usr/bin/env python3
"""
core/emails.py — Format d'email d'entreprise `prenom.nom@bmci.local`.

RÔLE
    Source de vérité UNIQUE du format d'adresse email :
      - `to_bnp_email(name)`      : dérive une adresse depuis un nom complet
                                     (accents translittérés, minuscules, alpha).
      - `unique_bnp_email(...)`   : idem avec résolution des collisions.
      - `is_valid_bnp_email(...)` : valide qu'une adresse respecte le format.

    Tout nouvel inscrit doit avoir une adresse de ce format ; les emails existants
    sont convertis (cf. database/init_db._migrate_emails).

EMPLACEMENT MVC
    Couche "core" : utilitaire transverse sans dépendance métier.
"""

import re
import unicodedata

EMAIL_DOMAIN = "bmci.local"
# prenom.nom (lettres) avec éventuel suffixe numérique de dédoublonnage.
_EMAIL_RE = re.compile(r"^[a-z]+\.[a-z]+[0-9]*@bmci.local$")


def _slug(text: str) -> str:
    """Minuscule, accents translittérés, lettres uniquement (é->e, ç->c, '-'/' ' retirés)."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z]", "", text).lower()


def to_bnp_email(name: str, suffix: str = "") -> str:
    """Dérive `prenom.nom@bmci.local` à partir d'un nom complet."""
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    if not parts:
        first, last = "utilisateur", "inconnu"
    elif len(parts) == 1:
        first, last = (_slug(parts[0]) or "utilisateur"), "user"
    else:
        first = _slug(parts[0]) or "utilisateur"
        last = _slug("".join(parts[1:])) or "user"
    return f"{first}.{last}{suffix}@{EMAIL_DOMAIN}"


def unique_bnp_email(name: str, taken: set) -> str:
    """Comme `to_bnp_email` mais garantit l'unicité vis-à-vis de `taken`
    (ensemble d'emails en minuscules) en ajoutant un suffixe numérique."""
    base = to_bnp_email(name)
    if base not in taken:
        return base
    local, domain = base.split("@", 1)
    i = 2
    while f"{local}{i}@{domain}" in taken:
        i += 1
    return f"{local}{i}@{domain}"


def is_valid_bnp_email(email: str) -> bool:
    """True si l'adresse respecte le format `prenom.nom@bmci.local`."""
    return bool(_EMAIL_RE.match((email or "").strip().lower()))
