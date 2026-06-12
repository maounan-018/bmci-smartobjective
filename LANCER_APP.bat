@echo off
setlocal enabledelayedexpansion
title ObjectifSMART-AI BMCI - Demarrage
color 0A
set "ROOT=%~dp0"

echo.
echo ================================================
echo   ObjectifSMART-AI BMCI - Demarrage complet
echo ================================================
echo.

REM ============================================================
REM [1/7] Python installe ?
REM ============================================================
echo [1/7] Verification de Python...
where python >nul 2>&1
if errorlevel 1 (
    echo     [ERREUR] Python introuvable dans le PATH.
    echo              Installe Python 3.10+ : https://www.python.org/downloads/
    echo              IMPORTANT : coche "Add Python to PATH" pendant l'installation.
    pause
    exit /b 1
)
echo     Python OK

REM ============================================================
REM [2/7] Node.js / npm installe ?
REM ============================================================
echo [2/7] Verification de Node.js / npm...
where npm >nul 2>&1
if errorlevel 1 (
    echo     [ERREUR] npm introuvable dans le PATH.
    echo              Installe Node.js 18+ : https://nodejs.org/
    pause
    exit /b 1
)
echo     Node/npm OK

REM ============================================================
REM [3/7] Fichiers critiques presents et non vides ?
REM    (detecte une copie corrompue : fichiers a 0 octet)
REM ============================================================
echo [3/7] Verification de l'integrite des fichiers...
set "INTEGRITE_OK=1"
for %%F in ("%ROOT%backend\.env" "%ROOT%backend\app\main.py" "%ROOT%requirements.txt" "%ROOT%frontend\package.json" "%ROOT%frontend\vite.config.js") do (
    if not exist "%%~F" (
        echo     [ERREUR] Fichier manquant : %%~F
        set "INTEGRITE_OK="
    ) else if %%~zF EQU 0 (
        echo     [ERREUR] Fichier VIDE ^(copie corrompue^) : %%~F
        set "INTEGRITE_OK="
    )
)
if not defined INTEGRITE_OK (
    echo.
    echo     La copie du projet semble incomplete ou corrompue.
    echo     Re-clone le projet ^(git clone^) ou recopie le dossier entier.
    pause
    exit /b 1
)
echo     Fichiers OK

REM ============================================================
REM [4/7] Dependances Python (idempotent)
REM ============================================================
echo [4/7] Installation des dependances Python (peut prendre 1-2 min)...
python -m pip install --disable-pip-version-check -q -r "%ROOT%requirements.txt"
if errorlevel 1 (
    echo     [ERREUR] L'installation des dependances Python a echoue.
    echo              Verifie ta connexion internet puis relance.
    pause
    exit /b 1
)
echo     Dependances Python OK

REM ============================================================
REM [5/7] Dependances Frontend (npm install si node_modules absent)
REM ============================================================
echo [5/7] Installation des dependances Frontend...
if not exist "%ROOT%frontend\node_modules" (
    echo     node_modules absent, npm install en cours... (peut prendre 2-3 min)
    pushd "%ROOT%frontend"
    call npm install
    set "NPM_RC=!errorlevel!"
    popd
    if not "!NPM_RC!"=="0" (
        echo     [ERREUR] npm install a echoue.
        pause
        exit /b 1
    )
) else (
    echo     node_modules deja present
)
echo     Dependances Frontend OK

REM ============================================================
REM [6/7] Ollama + modele smart-qwen8 (construit depuis Modelfile)
REM ============================================================
echo [6/7] Verification d'Ollama et du modele IA...
set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "!OLLAMA!" (
    where ollama >nul 2>&1
    if errorlevel 1 (
        echo     [ATTENTION] Ollama introuvable. L'analyse IA ne fonctionnera pas.
        echo                 Installe-le depuis https://ollama.com/download puis relance.
        echo                 (L'application demarre quand meme : connexion + interface OK.)
        set "OLLAMA="
    ) else (
        set "OLLAMA=ollama"
    )
)
if defined OLLAMA (
    start "Ollama" /min cmd /c ""!OLLAMA!" serve"
    timeout /t 3 /nobreak >nul
    "!OLLAMA!" list 2>nul | findstr /i "smart-qwen8" >nul 2>&1
    if errorlevel 1 (
        echo     Modele smart-qwen8 absent. Construction depuis le Modelfile...
        echo     (telecharge la base qwen3:8b si besoin - volumineux, patiente)
        "!OLLAMA!" pull qwen3:8b
        "!OLLAMA!" create smart-qwen8 -f "%~dp0Modelfile"
    )
    echo     Ollama OK
)

REM ============================================================
REM [7/7] Backend FastAPI + Frontend Vue
REM ============================================================
echo [7/7] Demarrage Backend (port 5001) et Frontend (port 3000)...
start "Backend FastAPI" cmd /k "cd /d "%ROOT%backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload"
timeout /t 5 /nobreak >nul
start "Frontend Vue" cmd /k "cd /d "%ROOT%frontend" && npm run dev"
timeout /t 5 /nobreak >nul

echo.
echo ================================================
echo   TOUT EST DEMARRE !
echo ================================================
echo.
echo   Application : http://localhost:3000
echo.
echo   Comptes de demonstration (crees automatiquement) :
echo     RH        : hr@bmci.ma      / REDACTED_DEMO_PWD
echo     Manager   : manager@bmci.ma / REDACTED_DEMO_PWD
echo     Collab    : collab@bmci.ma  / REDACTED_DEMO_PWD
echo.
echo   (Mots de passe a changer hors developpement.)
echo.
echo   Appuie sur une touche pour ouvrir le navigateur...
pause >nul
start "" "http://localhost:3000"
exit /b 0
