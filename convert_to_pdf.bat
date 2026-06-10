@echo off
setlocal enabledelayedexpansion
title Convertisseur PDF + ZIP
color 0B
cls

echo.
echo  ================================================
echo    CONVERTISSEUR PDF + ZIP  (100%% Windows natif)
echo    Aucune dependance - Double-clic pour lancer
echo  ================================================
echo.

REM === Dossier source ===
echo  Glisse ton dossier ici puis ENTREE
echo  (vide = dossier courant du .bat)
echo.
set /p "SRC_INPUT=  Source : "
set "SRC_INPUT=%SRC_INPUT:"=%"

if "!SRC_INPUT!"=="" (
    set "SRC=%~dp0"
    set "SRC=!SRC:~0,-1!"
) else (
    set "SRC=!SRC_INPUT!"
)

if not exist "!SRC!" (
    echo.
    echo  [ERREUR] Dossier introuvable : !SRC!
    pause & exit /b 1
)

REM === Dossier sortie automatique ===
for %%F in ("!SRC!") do (
    set "PARENT=%%~dpF"
    set "BASENAME=%%~nxF"
)
set "DST=!PARENT!!BASENAME!_pdf"
set "ZIPFILE=!PARENT!!BASENAME!_pdf.zip"

echo.
echo  Source  : !SRC!
echo  Sortie  : !DST!
echo  ZIP     : !ZIPFILE!
echo.
echo  Conversion en cours...
echo.

REM === Ecrire le script PowerShell dans un fichier temporaire ===
set "PS_TMP=%TEMP%\conv_pdf_%RANDOM%.ps1"

(
echo $SRC = '!SRC!'
echo $DST = '!DST!'
echo $ZIPFILE = '!ZIPFILE!'
echo.
echo $SKIP_DIRS = @('node_modules','__pycache__','.git','.venv','venv','dist','build','.next','.nuxt','.pytest_cache','.idea','.vscode','coverage','.mypy_cache')
echo $SKIP_EXTS = @('.pyc','.pyo','.pyd','.exe','.dll','.so','.jpg','.jpeg','.png','.gif','.ico','.svg','.bmp','.webp','.mp4','.mp3','.avi','.zip','.tar','.gz','.rar','.7z','.db','.sqlite','.sqlite3','.pdf','.woff','.woff2','.ttf','.eot')
echo $LINES_PER_PAGE = 60
echo $ENC = [System.Text.Encoding]::Latin1
echo.
echo function Escape-Pdf($s) {
echo     if ($null -eq $s) { return '' }
echo     $s = $s -replace '\','`\`\'
echo     $s = $s -replace '\(','`\('
echo     $s = $s -replace '\)','`\)'
echo     if ($s.Length -gt 155) { $s = $s.Substring(0,155) + '...' }
echo     return $s
echo }
echo.
echo function New-PDF($srcPath, $dstPath, $relPath) {
echo     $lines = @()
echo     try {
echo         $raw = [System.IO.File]::ReadAllBytes($srcPath)
echo         if ($raw -contains 0) { $lines = @("[Fichier binaire]") }
echo         else {
echo             foreach ($enc2 in @([System.Text.Encoding]::UTF8,[System.Text.Encoding]::Default)) {
echo                 try { $lines = $enc2.GetString($raw) -split "`n" | ForEach-Object { $_ -replace "`r",'' }; break } catch {}
echo             }
echo         }
echo     } catch { $lines = @("[Erreur de lecture]") }
echo     if ($lines.Count -eq 0) { $lines = @("[Fichier vide]") }
echo.
echo     $total = $lines.Count
echo     $pages = [Math]::Max(1,[Math]::Ceiling($total / $LINES_PER_PAGE))
echo     $fontObj = 3 + 2*$pages
echo     $ms = New-Object System.IO.MemoryStream
echo     $off = @{}
echo.
echo     $wr = { param($s) $b=$ENC.GetBytes($s); $ms.Write($b,0,$b.Length) }
echo.
echo     & $wr "%%PDF-1.4`n"
echo.
echo     $kids = (1..$pages | ForEach-Object { "$( 2+$_) 0 R" }) -join ' '
echo.
echo     $off[1] = $ms.Position
echo     & $wr "1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n"
echo.
echo     $off[2] = $ms.Position
echo     & $wr "2 0 obj`n<< /Type /Pages /Kids [$kids] /Count $pages >>`nendobj`n"
echo.
echo     for ($p=0; $p -lt $pages; $p++) {
echo         $po=3+$p; $co=3+$pages+$p
echo         $off[$po]=$ms.Position
echo         & $wr "$po 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents $co 0 R /Resources << /Font << /F1 $fontObj 0 R >> >> >>`nendobj`n"
echo     }
echo.
echo     for ($p=0; $p -lt $pages; $p++) {
echo         $co=3+$pages+$p; $off[$co]=$ms.Position
echo         $sb=New-Object System.Text.StringBuilder
echo         $s=$p*$LINES_PER_PAGE; $e=[Math]::Min($s+$LINES_PER_PAGE,$total)
echo         if ($p -eq 0) {
echo             $h=Escape-Pdf $relPath
echo             [void]$sb.Append("BT`n/F1 9 Tf`n30 825 Td`n($h) Tj`n/F1 8 Tf`n30 808 Td`n10 TL`n")
echo         } else {
echo             $h=Escape-Pdf "$relPath  [p.$($p+1)/$pages]"
echo             [void]$sb.Append("BT`n/F1 7 Tf`n30 830 Td`n($h) Tj`n/F1 8 Tf`n30 815 Td`n10 TL`n")
echo         }
echo         for ($i=$s; $i -lt $e; $i++) { $esc=Escape-Pdf $lines[$i]; [void]$sb.Append("($esc) Tj T*`n") }
echo         [void]$sb.Append("ET")
echo         $sc=$sb.ToString(); $sb2=$ENC.GetBytes($sc); $sl=$sb2.Length
echo         & $wr "$co 0 obj`n<< /Length $sl >>`nstream`n"
echo         $ms.Write($sb2,0,$sb2.Length)
echo         & $wr "`nendstream`nendobj`n"
echo     }
echo.
echo     $off[$fontObj]=$ms.Position
echo     & $wr "$fontObj 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>`nendobj`n"
echo.
echo     $xo=$ms.Position
echo     $no=$fontObj+1
echo     & $wr "xref`n0 $no`n"
echo     & $wr "0000000000 65535 f `r`n"
echo     for ($i=1;$i -le $fontObj;$i++) { & $wr ("{0:D10} 00000 n `r`n" -f $off[$i]) }
echo     & $wr "trailer`n<< /Size $no /Root 1 0 R >>`nstartxref`n$xo`n%%%%EOF`n"
echo.
echo     [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($dstPath)) ^| Out-Null
echo     [System.IO.File]::WriteAllBytes($dstPath,$ms.ToArray())
echo     $ms.Dispose()
echo }
echo.
echo $total=0; $skip=0; $err=0
echo.
echo Get-ChildItem -Path $SRC -Recurse -File ^| ForEach-Object {
echo     $rel = $_.FullName.Substring($SRC.Length).TrimStart('\')
echo     $parts = $rel -split '\'
echo     $skipIt = $false
echo     foreach ($part in $parts) { if ($SKIP_DIRS -contains $part) { $skipIt=$true; break } }
echo     if (-not $skipIt -and ($SKIP_EXTS -contains $_.Extension.ToLower())) { $skipIt=$true }
echo     if ($skipIt) { $script:skip++; return }
echo     $noext = $rel -replace '\.[^.\]*$',''
echo     $dst2 = Join-Path $DST "$noext.pdf"
echo     try {
echo         New-PDF $_.FullName $dst2 $rel
echo         Write-Host "  [OK]  $rel" -ForegroundColor Green
echo         $script:total++
echo     } catch {
echo         Write-Host "  [ERR] $rel  ->  $_" -ForegroundColor Red
echo         $script:err++
echo     }
echo }
echo.
echo Write-Host ""
echo Write-Host "  Convertis : $total  ^|  Ignores : $skip  ^|  Erreurs : $err" -ForegroundColor Cyan
echo Write-Host ""
echo.
echo if (Test-Path $DST) {
echo     Write-Host "  Creation du ZIP..." -ForegroundColor Yellow
echo     if (Test-Path $ZIPFILE) { Remove-Item $ZIPFILE -Force }
echo     Compress-Archive -Path $DST -DestinationPath $ZIPFILE -Force
echo     Write-Host "  ZIP cree : $ZIPFILE" -ForegroundColor Green
echo }
) > "!PS_TMP!"

REM === Executer le script PowerShell ===
powershell -ExecutionPolicy Bypass -File "!PS_TMP!"

REM === Nettoyer le script temporaire ===
if exist "!PS_TMP!" del "!PS_TMP!"

REM === Ouvrir le dossier ZIP ===
echo.
if exist "!ZIPFILE!" (
    echo  ZIP disponible : !ZIPFILE!
    explorer /select,"!ZIPFILE!"
)

echo.
echo  ================================================
echo   TERMINE - Appuie sur une touche pour fermer.
echo  ================================================
pause >/dev/null
