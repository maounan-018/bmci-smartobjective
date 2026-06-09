@echo off
setlocal enabledelayedexpansion
title Convertisseur PDF
color 0B
cls

echo.
echo  ================================================
echo    CONVERTISSEUR DE FICHIERS EN PDF
echo    Arborescence conservee - Double-clic pour lancer
echo  ================================================
echo.

REM === Verifier Python ===
python --version >/dev/null 2>&1
if errorlevel 1 (
    echo  [ERREUR] Python non trouve.
    echo  Installe Python sur https://www.python.org/downloads/
    pause & exit /b 1
)

REM === Verifier reportlab ===
python -c "import reportlab" >/dev/null 2>&1
if errorlevel 1 (
    echo  [INFO] Installation de reportlab en cours...
    pip install reportlab
    if errorlevel 1 ( echo  [ERREUR] pip a echoue. & pause & exit /b 1 )
    echo  [OK] reportlab installe.
    echo.
)

REM === Dossier source ===
echo  Glisse un dossier ici puis ENTREE
echo  (vide = dossier courant)
echo.
set /p "SRC_INPUT=  Source : "
set "SRC_INPUT=%SRC_INPUT:"=%"

if "%SRC_INPUT%"=="" (
    set "SRC=%~dp0"
    set "SRC=!SRC:~0,-1!"
) else (
    set "SRC=%SRC_INPUT%"
)

if not exist "!SRC!" (
    echo  [ERREUR] Dossier introuvable : !SRC!
    pause & exit /b 1
)

REM === Dossier sortie ===
echo.
echo  Dossier de SORTIE (vide = cree automatiquement "[nom]_pdf")
echo.
set /p "DST_INPUT=  Sortie  : "
set "DST_INPUT=%DST_INPUT:"=%"

REM === Lancer la conversion ===
echo.
echo  Conversion en cours...
echo  Source : !SRC!
echo.

set "SCRIPT=%~dp0convert_to_pdf.py"
if not exist "!SCRIPT!" (
    echo  [ERREUR] convert_to_pdf.py introuvable.
    echo  Place convert_to_pdf.py dans le meme dossier que ce .bat
    pause & exit /b 1
)

if "!DST_INPUT!"=="" (
    python "!SCRIPT!" "!SRC!"
) else (
    python "!SCRIPT!" "!SRC!" "!DST_INPUT!"
)

if errorlevel 1 ( echo  [ERREUR] Conversion echouee. & pause & exit /b 1 )

REM === Ouvrir le dossier resultat ===
echo.
if "!DST_INPUT!"=="" (
    for %%F in ("!SRC!") do set "AUTO_DST=%%~dpF%%~nxF_pdf"
    if exist "!AUTO_DST!" start "" "!AUTO_DST!"
) else (
    if exist "!DST_INPUT!" start "" "!DST_INPUT!"
)

echo  ================================================
echo   TERMINE - Le dossier PDF s'est ouvert.
echo  ================================================
echo.
pause >/dev/null
