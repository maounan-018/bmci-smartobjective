#!/usr/bin/env python3
"""
tests/test_hr_import.py — Tests de securite de l'import Excel RH.

Couvre F10 : les comptes COLLAB crees a la volee a partir d'un fichier Excel
doivent recevoir un mot de passe aleatoire FORT (token_urlsafe), JAMAIS le
SEED_COLLAB_PASSWORD partage. Les credentials temporaires sont retournes
dans la reponse `created_users` pour transmission individuelle par le HR.
"""

import io

import openpyxl


def test_import_creates_users_with_random_distinct_passwords(client, make_user, auth_token):
    """Chaque compte cree doit avoir un mot de passe unique, fort, non-seed."""
    # 1. HR connecte
    make_user(user_id="hr-test", email="hr-test@bmci.test", role="HR")
    token = auth_token("hr-test")

    # 2. Excel minimal en memoire avec 2 collaborateurs
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Email", "Nom", "Titre"])
    ws.append(["alice@bmci.test", "Alice Imported", "Augmenter NPS de 10% d'ici fin 2026"])
    ws.append(["bob@bmci.test", "Bob Imported", "Reduire delai traitement de 20% au T2"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    # 3. Import via /api/hr/import-objectives
    resp = client.post(
        "/api/hr/import-objectives",
        files={
            "file": (
                "test.xlsx",
                buf,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["users_created"] == 2
    assert "created_users" in body, "La reponse doit inclure les credentials temporaires"

    creds = body["created_users"]
    assert len(creds) == 2

    # 4. Mots de passe distincts (pas tous le meme seed)
    passwords = [c["temporary_password"] for c in creds]
    assert len(set(passwords)) == 2, "Chaque compte doit avoir un mot de passe UNIQUE"

    # 5. Longueur suffisante (token_urlsafe(16) produit ~22 chars base64url)
    assert all(len(p) >= 16 for p in passwords), "Mot de passe trop court"

    # 6. Aucun mot de passe ne doit etre le seed connu (F10 historique)
    assert "REDACTED_DEMO_PWD" not in passwords
    assert "REDACTED_DEMO_PWD" not in passwords
    assert "REDACTED_DEMO_PWD" not in passwords

    # 7. Chaque entree doit etre nominative
    emails = {c["email"] for c in creds}
    assert emails == {"alice@bmci.test", "bob@bmci.test"}


def test_import_existing_user_not_recreated(client, make_user, auth_token):
    """Un email deja en base ne doit PAS reapparaitre dans created_users."""
    make_user(user_id="hr-test", email="hr-test@bmci.test", role="HR")
    token = auth_token("hr-test")

    # Cree un collab existant
    make_user(user_id="u-existing", email="existing@bmci.test", role="COLLAB")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Email", "Nom", "Titre"])
    ws.append(["existing@bmci.test", "Existing", "Objectif test"])
    ws.append(["new@bmci.test", "New", "Autre objectif"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = client.post(
        "/api/hr/import-objectives",
        files={"file": ("test.xlsx", buf,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    body = resp.json()
    # Seul "new" est cree, donc 1 seul credential temporaire
    assert body["users_created"] == 1
    assert len(body["created_users"]) == 1
    assert body["created_users"][0]["email"] == "new@bmci.test"
