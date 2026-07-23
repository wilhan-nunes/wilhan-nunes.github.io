#!/bin/bash

if [[ -z "$1" ]]; then
    echo "Usage: $0 <doi_list.txt>"
    exit 1
fi

# Ensure biber is available for formatting
if ! command -v biber &>/dev/null; then
    echo "biber not found — installing via Homebrew..."
    if ! command -v brew &>/dev/null; then
        echo "Error: Homebrew is required to install biber. Install it from https://brew.sh" >&2
        exit 1
    fi
    brew install biber
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOI_LIST="$1"

while IFS= read -r DOI || [[ -n "$DOI" ]]; do
    [[ -z "$DOI" ]] && continue
    OUTPUT_FILE="$SCRIPT_DIR/${DOI//\//_}.bib"

    if [[ -f "$OUTPUT_FILE" ]]; then
        echo "Skipping existing: $DOI"
        continue
    fi

    echo "Fetching: $DOI"
    curl -LH "Accept: application/x-bibtex" "https://doi.org/${DOI}" -o "$OUTPUT_FILE"

    echo "Formatting: $OUTPUT_FILE"
    biber --tool --quiet --output-legacy-dates --output-file="$OUTPUT_FILE" "$OUTPUT_FILE" 2>/dev/null \
        && rm -f "${OUTPUT_FILE}.blg" \
        || echo "Warning: biber could not format $OUTPUT_FILE (entry may be non-standard)"
done < "$DOI_LIST"
