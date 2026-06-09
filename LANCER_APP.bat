@echo off
title ObjectifSMART-AI BMCI - Demarrage
color 0A
echo.
echo ================================================
echo   ObjectifSMART-AI BMCI - Demarrage complet
echo ================================================
echo.

REM === ETAPE 1 : Le .env est deja committe dans backend\.env ===
REM Un seul env, identique en local et sur GitHub. Plus de generation ici :
REM le fichier backend\.env est versionne dans le depot.
echo [1/4] Verification du backend\.env committe...
if not exist "%~dp0backend\.env" (
    echo     [ERREUR] backend\.env introuvable. Il devrait etre versionne dans le depot.
    pause
    exit /b 1
)
echo     .env present OK

REM === ETAPE 2 : Demarrer Ollama ===
echo [2/4] Demarrage Ollama...
start "Ollama" /min cmd /c ""%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve"
timeout /t 3 /nobreak >/dev/null
echo     Ollama demarre OK

REM === ETAPE 3 : Demarrer le Backend ===
echo [3/4] Demarrage Backend FastAPI (port 5001)...
start "Backend FastAPI" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload"
timeout /t 4 /nobreak >/dev/null
echo     Backend demarre OK

REM === ETAPE 4 : Demarrer le Frontend ===
echo [4/4] Demarrage Frontend Vue (port 3000)...
start "Frontend Vue" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 4 /nobreak >/dev/null
echo     Frontend demarre OK

echo.
echo ================================================
echo   TOUT EST DEMARRE !
echo ================================================
echo.
echo   Ouvre le navigateur sur :
echo   http://localhost:3000
echo.
echo   Comptes de connexion :
echo   HR        : hr@bmci.ma     / REDACTED_DEMO_PWD
echo   Manager   : manager@bmci.ma / REDACTED_DEMO_PWD
echo   Collab    : collab@bmci.ma  / REDACTED_DEMO_PWD
echo.
echo   Appuie sur une touche pour ouvrir le navigateur...
pause >/dev/null
start "" "http://localhost:3000"
