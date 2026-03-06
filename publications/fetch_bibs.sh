#!/bin/bash

if [[ -z "$1" ]]; then
    echo "Usage: $0 <doi_list.txt>"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOI_LIST="$1"

while IFS= read -r DOI; do
    [[ -z "$DOI" ]] && continue
    echo "Fetching: $DOI"
    curl -LH "Accept: application/x-bibtex" "https://doi.org/${DOI}" -o "$SCRIPT_DIR/${DOI//\//_}.bib"
done < "$DOI_LIST"
