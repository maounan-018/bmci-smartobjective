@echo off
title ObjectifSMART-AI - BMCI
echo ============================================================
echo    ObjectifSMART-AI - BMCI
echo    Demarrage de l'application...
echo ============================================================
echo.

REM Vérifier si Ollama est installé
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Ollama n'est pas installe!
    echo Telechargez-le depuis: https://ollama.com
    pause
    exit /b 1
)

REM Vérifier si le modèle existe
ollama list | findstr "smart-qwen8" >nul
if %errorlevel% neq 0 (
    echo [INFO] Creation du modele smart-qwen8...
    ollama create smart-qwen8 -f Modelfile
)

echo [1/3] Demarrage d'Ollama en arriere-plan...
start /min cmd /c "ollama serve"
timeout /t 3 >nul

echo [2/3] Demarrage du backend FastAPI (MVC, port 5001)...
start /min cmd /c "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload"
timeout /t 2 >nul

echo [3/3] Demarrage du frontend Vue.js (port 3000)...
start cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ============================================================
echo    Application demarree!
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:5001
echo ============================================================
echo.
echo Appuyez sur une touche pour fermer cette fenetre...
pause >nul
