#!/usr/bin/env bash
# =============================================================================
# convert_to_pdf.sh — Convertit tous les fichiers d'un dossier en PDF
# Conserve l'arborescence exacte. Aucune dépendance externe (bash pur).
#
# Usage :
#   bash convert_to_pdf.sh                       # dossier courant
#   bash convert_to_pdf.sh /mon/projet           # dossier précis
#   bash convert_to_pdf.sh /mon/projet /sortie   # dossier de sortie custom
# =============================================================================

set -euo pipefail

# ── Dossiers à ignorer ────────────────────────────────────────────────────────
SKIP_DIRS="node_modules __pycache__ .git .venv venv dist build .next .nuxt
           .pytest_cache .idea .vscode coverage .mypy_cache __MACOSX"

# ── Extensions à ignorer (binaires, images, archives) ────────────────────────
SKIP_EXTS="pyc pyo pyd exe dll so dylib
           jpg jpeg png gif ico svg bmp webp tiff
           mp4 mp3 avi mov wav
           zip tar gz rar 7z
           db sqlite sqlite3
           pdf woff woff2 ttf eot"

LINES_PER_PAGE=60

# ── Échappe les caractères spéciaux pour les chaînes PDF ─────────────────────
pdf_escape() {
    local s="$1"
    s="${s//\\/\\\\}"   # \ -> \\
    s="${s//(/\\(}"      # ( -> \(
    s="${s//)/\\)}"      # ) -> \)
    # Tronque les lignes trop longues
    if (( ${#s} > 160 )); then s="${s:0:160}..."; fi
    printf '%s' "$s"
}

# ── Génère un PDF pour un fichier source ─────────────────────────────────────
generate_pdf() {
    local src="$1"
    local dst="$2"
    local relpath="$3"
    local tmp="${dst}.tmp$$"

    mkdir -p "$(dirname "$dst")"

    # ── Lecture du fichier ────────────────────────────────────────────────────
    local -a lines=()

    # Détection binaire rapide (octets null)
    if LC_ALL=C grep -qP '\x00' "$src" 2>/dev/null; then
        lines=("[Fichier binaire — contenu non affichable]")
    else
        local lnum=0
        while IFS= read -r line || [[ -n "$line" ]]; do
            lines+=("$line")
            (( lnum++ )) || true
        done < "$src" 2>/dev/null || lines=("[Erreur de lecture]")
    fi

    [[ ${#lines[@]} -eq 0 ]] && lines=("[Fichier vide]")

    local total_lines=${#lines[@]}
    local pages=$(( (total_lines + LINES_PER_PAGE - 1) / LINES_PER_PAGE ))
    (( pages == 0 )) && pages=1

    # ── Numérotation des objets PDF ───────────────────────────────────────────
    # 1       = Catalog
    # 2       = Pages
    # 3..(2+pages)           = Page objects
    # (3+pages)..(2+2*pages) = Content streams
    # (3+2*pages)            = Font
    local font_obj=$(( 3 + 2 * pages ))

    # ── Écriture progressive dans tmp ────────────────────────────────────────
    > "$tmp"

    # Offset courant (recalculé après chaque écriture)
    off() { wc -c < "$tmp"; }

    wr() { printf '%s' "$1" >> "$tmp"; }

    # En-tête PDF
    wr $'%PDF-1.4\n'

    # ── Objet 1 : Catalog ────────────────────────────────────────────────────
    local -a offs=()
    offs[1]=$(off)
    wr $'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'

    # ── Objet 2 : Pages ──────────────────────────────────────────────────────
    local kids=""
    for (( p=0; p<pages; p++ )); do kids+="$(( 3+p )) 0 R "; done
    offs[2]=$(off)
    wr "$(printf '2 0 obj\n<< /Type /Pages /Kids [%s] /Count %d >>\nendobj\n' \
        "$kids" "$pages")"

    # ── Objets Page (3 .. 2+pages) ───────────────────────────────────────────
    for (( p=0; p<pages; p++ )); do
        local po=$(( 3+p ))
        local co=$(( 3+pages+p ))
        offs[$po]=$(off)
        wr "$(printf '%d 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>\nendobj\n' \
            "$po" "$co" "$font_obj")"
    done

    # ── Flux de contenu (3+pages .. 2+2*pages) ───────────────────────────────
    for (( p=0; p<pages; p++ )); do
        local co=$(( 3+pages+p ))
        offs[$co]=$(off)

        # Construction du flux BT ... ET
        local stream=""

        if (( p == 0 )); then
            # Titre : nom du fichier en haut de la 1ère page
            local header
            header=$(pdf_escape "=== ${relpath} ===")
            stream+="BT\n"
            stream+="/F1 9 Tf\n30 825 Td\n"
            stream+="(${header}) Tj\n"
            stream+="/F1 8 Tf\n30 808 Td\n10 TL\n"
        else
            local page_header
            page_header=$(pdf_escape "${relpath}  [page $((p+1))/$pages]")
            stream+="BT\n"
            stream+="/F1 7 Tf\n30 830 Td\n"
            stream+="(${page_header}) Tj\n"
            stream+="/F1 8 Tf\n30 815 Td\n10 TL\n"
        fi

        local start=$(( p * LINES_PER_PAGE ))
        local end=$(( start + LINES_PER_PAGE ))
        (( end > total_lines )) && end=$total_lines

        for (( i=start; i<end; i++ )); do
            local escaped
            escaped=$(pdf_escape "${lines[$i]}")
            stream+="(${escaped}) Tj T*\n"
        done
        stream+="ET"

        # Rendu et mesure de la longueur (en octets)
        local rendered
        rendered=$(printf '%b' "$stream")
        local slen
        slen=$(printf '%s' "$rendered" | wc -c)

        wr "$(printf '%d 0 obj\n<< /Length %d >>\nstream\n' "$co" "$slen")"
        printf '%s\n' "$rendered" >> "$tmp"
        wr $'endstream\nendobj\n'
    done

    # ── Objet Font ───────────────────────────────────────────────────────────
    offs[$font_obj]=$(off)
    wr "$(printf '%d 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n' \
        "$font_obj")"

    # ── Table xref ───────────────────────────────────────────────────────────
    local xref_off
    xref_off=$(off)
    local nobjs=$(( font_obj + 1 ))

    wr "$(printf 'xref\n0 %d\n' "$nobjs")"
    wr "$(printf '0000000000 65535 f \r\n')"
    for (( i=1; i<=font_obj; i++ )); do
        wr "$(printf '%010d 00000 n \r\n' "${offs[$i]}")"
    done

    # ── Trailer ──────────────────────────────────────────────────────────────
    wr "$(printf 'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' \
        "$nobjs" "$xref_off")"

    mv "$tmp" "$dst"
}

# ── Vérifie si un chemin contient un dossier à ignorer ───────────────────────
is_skip_dir() {
    local relpath="$1"
    for sd in $SKIP_DIRS; do
        if [[ "$relpath" == "$sd"/* || "$relpath" == *"/$sd"/* || "$relpath" == "$sd" ]]; then
            return 0
        fi
    done
    return 1
}

# ── Vérifie si l'extension est à ignorer ─────────────────────────────────────
is_skip_ext() {
    local ext="${1##*.}"
    ext="${ext,,}"
    for se in $SKIP_EXTS; do
        [[ "$ext" == "$se" ]] && return 0
    done
    return 1
}

# ── Point d'entrée ───────────────────────────────────────────────────────────
SRC="$(realpath "${1:-$(pwd)}")"
BASE="$(basename "$SRC")"
DST="$(realpath "${2:-$(dirname "$SRC")/${BASE}_pdf}")"

printf '\n%s\n' "================================================"
printf '  CONVERSION PDF — bash pur (aucune dépendance)\n'
printf '  Source : %s\n' "$SRC"
printf '  Sortie : %s\n' "$DST"
printf '%s\n\n' "================================================"

total=0; skipped=0; errors=0

while IFS= read -r -d '' filepath; do
    relpath="${filepath#"$SRC"/}"

    # Ignorer les dossiers exclus
    is_skip_dir "$relpath" && continue

    # Ignorer les extensions exclues
    if is_skip_ext "$filepath"; then
        (( skipped++ )) || true
        continue
    fi

    # Chemin de destination (même arbre, extension -> .pdf)
    local_noext="${filepath%.*}"
    rel_noext="${local_noext#"$SRC"/}"
    dst_path="${DST}/${rel_noext}.pdf"

    if generate_pdf "$filepath" "$dst_path" "$relpath" 2>/dev/null; then
        printf '  [OK]   %s\n' "$relpath"
        (( total++ )) || true
    else
        printf '  [ERR]  %s\n' "$relpath"
        (( errors++ )) || true
    fi

done < <(find "$SRC" -type f -print0 2>/dev/null | sort -z)

printf '\n%s\n' "================================================"
printf '  RÉSULTAT\n'
printf '  Convertis : %d\n' "$total"
printf '  Ignorés   : %d  (binaires, images, .pyc...)\n' "$skipped"
printf '  Erreurs   : %d\n' "$errors"
printf '  Dossier   : %s\n' "$DST"
printf '%s\n\n' "================================================"
