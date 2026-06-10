@echo off
setlocal enabledelayedexpansion
title Reverse PDF — Restauration des fichiers originaux
color 0A
cls

echo.
echo  ================================================
echo    REVERSE PDF — Restauration fichiers originaux
echo    Lit les PDFs et restaure l arbre original
echo  ================================================
echo.

REM === Dossier source (le dossier _pdf) ===
echo  Glisse le dossier _pdf ici puis ENTREE
echo  (vide = cherche un dossier _pdf dans le dossier courant)
echo.
set /p "SRC_INPUT=  Source (_pdf) : "
set "SRC_INPUT=%SRC_INPUT:"=%"

if "!SRC_INPUT!"=="" (
    for /d %%D in ("%~dp0*_pdf") do (
        set "SRC=%%D"
        goto :found_src
    )
    echo  [ERREUR] Aucun dossier _pdf trouve.
    pause & exit /b 1
    :found_src
) else (
    set "SRC=!SRC_INPUT!"
)

if not exist "!SRC!" (
    echo  [ERREUR] Dossier introuvable : !SRC!
    pause & exit /b 1
)

REM === Dossier de sortie ===
for %%F in ("!SRC!") do (
    set "PARENT=%%~dpF"
    set "BASENAME=%%~nxF"
)
set "BASENAME_CLEAN=!BASENAME:_pdf=!"
set "DST=!PARENT!!BASENAME_CLEAN!_restored"

echo.
echo  Source  : !SRC!
echo  Sortie  : !DST!
echo.
echo  Restauration en cours...
echo.

REM === Ecrire le script PowerShell dans temp ===
set "PS_TMP=%TEMP%\reverse_pdf_%RANDOM%.ps1"

(
echo $SRC = '!SRC!'
echo $DST = '!DST!'
echo $total = 0; $skip = 0; $err = 0
echo.
echo function Unescape-PDF($s) {
echo     $s = $s -replace '\\(', '('
echo     $s = $s -replace '\\)', ')'
echo     $s = $s -replace '\\', '\'
echo     return $s
echo }
echo.
echo function Restore-FromPDF($pdfPath) {
echo     $bytes  = [System.IO.File]::ReadAllBytes($pdfPath)
echo     $raw    = [System.Text.Encoding]::Latin1.GetString($bytes)
echo.
echo     # Extraire tous les flux de contenu (entre stream et endstream)
echo     $streams = [regex]::Matches($raw, 'stream\r?\n(.*?)\r?\nendstream', [System.Text.RegularExpressions.RegexOptions]::Singleline)
echo.
echo     $origPath  = $null
echo     $allLines  = [System.Collections.Generic.List[string]]::new()
echo     $firstLine = $true
echo.
echo     foreach ($sm in $streams) {
echo         $block = $sm.Groups[1].Value
echo         # Extraire toutes les chaines PDF : (contenu) Tj
echo         $tjs = [regex]::Matches($block, '\(([^\)]*(?:\.[^\)]*)*)\)\s*Tj')
echo         foreach ($tj in $tjs) {
echo             $line = Unescape-PDF $tj.Groups[1].Value
echo             if ($firstLine) {
echo                 # 1ere ligne = en-tete "=== chemin/original.ext ==="
echo                 if ($line -match '^===\s+(.+?)\s+===$') {
echo                     $origPath = $matches[1]
echo                 }
echo                 $firstLine = $false
echo                 continue
echo             }
echo             # Ignorer les en-tetes de pages suivantes "[p.X/Y]"
echo             if ($line -match '\[p\.\d+/\d+\]') { continue }
echo             $allLines.Add($line)
echo         }
echo     }
echo.
echo     return @{ Path = $origPath; Lines = $allLines }
echo }
echo.
echo # Parcourir tous les PDFs
echo Get-ChildItem -Path $SRC -Recurse -Filter '*.pdf' ^| ForEach-Object {
echo     $pdfFile = $_.FullName
echo     try {
echo         $result = Restore-FromPDF $pdfFile
echo.
echo         if ($result.Path) {
echo             # Utiliser le chemin original extrait du PDF
echo             $outPath = Join-Path $DST $result.Path
echo         } else {
echo             # Fallback : meme chemin relatif sans .pdf
echo             $rel     = $_.FullName.Substring($SRC.Length).TrimStart('\')
echo             $noext   = $rel -replace '\.pdf$',''
echo             $outPath = Join-Path $DST $noext
echo         }
echo.
echo         # Creer le dossier parent
echo         $dir = [System.IO.Path]::GetDirectoryName($outPath)
echo         [System.IO.Directory]::CreateDirectory($dir) ^| Out-Null
echo.
echo         # Ecrire le fichier restaure
echo         $content = $result.Lines -join "`n"
echo         [System.IO.File]::WriteAllText($outPath, $content, [System.Text.Encoding]::UTF8)
echo.
echo         Write-Host "  [OK]  $($result.Path ?? $_.Name)" -ForegroundColor Green
echo         $script:total++
echo     } catch {
echo         Write-Host "  [ERR] $($_.Name)  ->  $_" -ForegroundColor Red
echo         $script:err++
echo     }
echo }
echo.
echo Write-Host ""
echo Write-Host "  Restaures : $total  ^|  Erreurs : $err" -ForegroundColor Cyan
echo Write-Host "  Dossier   : $DST" -ForegroundColor Cyan
echo Write-Host ""
) > "!PS_TMP!"

REM === Executer ===
powershell -ExecutionPolicy Bypass -File "!PS_TMP!"

REM === Nettoyer ===
if exist "!PS_TMP!" del "!PS_TMP!"

REM === Ouvrir le resultat ===
if exist "!DST!" (
    echo  Ouverture du dossier restaure...
    explorer "!DST!"
)

echo.
echo  ================================================
echo   TERMINE - Appuie sur une touche pour fermer.
echo  ================================================
pause >/dev/null
