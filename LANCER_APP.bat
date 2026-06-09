@echo off
title ObjectifSMART-AI BMCI - Demarrage
color 0A
echo.
echo ================================================
echo   ObjectifSMART-AI BMCI - Demarrage complet
echo ================================================
echo.

REM === ETAPE 1 : Creer le .env avec toutes les variables ===
echo [1/4] Creation du fichier .env...
(
echo APP_NAME=ObjectifSMART-AI
echo OLLAMA_URL=http://localhost:11434/api/generate
echo OLLAMA_MODEL=qwen3:4b
echo DATABASE_PATH=objectifsmart.db
echo SECRET_KEY=bmci-secret-key-32-caracteres-minimum-2026
echo SESSION_DURATION_HOURS=24
echo PBKDF2_ITERATIONS=200000
echo MAX_LOGIN_ATTEMPTS=5
echo LOGIN_LOCKOUT_MINUTES=15
echo ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173
echo SEED_MANAGER_PASSWORD=REDACTED_DEMO_PWD
echo SEED_HR_PASSWORD=REDACTED_DEMO_PWD
echo SEED_COLLAB_PASSWORD=REDACTED_DEMO_PWD
) > "%~dp0backend\.env"
echo     .env cree OK

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
