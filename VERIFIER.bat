@echo off
REM ============================================================
REM VERIFIER.bat - Diagnostic "pret a demarrer" (double-clic).
REM Lance verif_projet.py et garde la fenetre ouverte pour lire
REM le resultat. N'installe rien, ne modifie rien.
REM ============================================================
title ObjectifSMART-AI - Diagnostic
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable dans le PATH.
    echo          Installe Python 3.10+ : https://www.python.org/downloads/
    echo          IMPORTANT : coche "Add Python to PATH" pendant l'installation.
    echo.
    pause
    exit /b 1
)

python "%~dp0verif_projet.py"

echo.
echo Appuie sur une touche pour fermer...
pause >nul
