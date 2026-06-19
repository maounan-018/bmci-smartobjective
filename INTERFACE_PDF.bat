@echo off
REM ============================================================
REM INTERFACE_PDF.bat - Ouvre l'interface graphique des outils PDF.
REM Double-clic : transforme le code en PDF, ou reconstruit le code.
REM ============================================================
title Outil PDF - Interface
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable dans le PATH.
    echo          Installe Python 3.10+ : https://www.python.org/downloads/
    echo          IMPORTANT : coche "Add Python to PATH".
    pause
    exit /b 1
)

python "%~dp0interface_pdf.py"
