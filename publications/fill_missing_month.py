#!/usr/bin/env python3
"""
fill_missing_month.py <bib_file> <doi>

doi.org's `Accept: application/x-bibtex` transform sometimes omits the
`month` field even when Crossref's own record has a full date. This
script parses the .bib file, backfills `month` from Crossref's JSON API
if missing, normalizes it to a lowercase 3-letter macro, and rewrites
the file in a consistent, human-readable format.
"""
import json
import re
import sys
import urllib.request

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]
FULL_NAMES = ["january", "february", "march", "april", "may", "june",
              "july", "august", "september", "october", "november", "december"]

FIELD_ORDER = ["title", "volume", "issn", "url", "doi", "number",
               "journal", "publisher", "author", "year", "month", "pages"]


def get_month_from_crossref(doi: str) -> str | None:
    url = f"https://api.crossref.org/works/{doi}"
    req = urllib.request.Request(url, headers={"User-Agent": "git-cv-build/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)["message"]

    for key in ("published-print", "published-online", "issued", "created"):
        parts = data.get(key, {}).get("date-parts", [[None]])[0]
        if len(parts) >= 2 and parts[1]:
            return MONTHS[parts[1] - 1]
    return None


def brace_bare_month_names(text: str) -> str:
    """doi.org sometimes emits `month=July` as a bare (unquoted) word, which
    bibtexparser treats as an undefined string macro (only 3-letter abbrevs
    like `jul` are predefined). Brace full month names so they parse as
    literal strings instead."""
    def repl(match: re.Match) -> str:
        word = match.group(2)
        if word.lower() in MONTHS:
            return match.group(0)  # standard 3-letter macro, leave bare
        return f"{match.group(1)}{{{word}}}"

    return re.sub(r"(month\s*=\s*)([A-Za-z]+)(?=[,}\s])", repl, text, flags=re.IGNORECASE)


def normalize_month(value: str) -> str:
    raw = value.strip().lower()
    if raw in MONTHS:
        return raw
    if raw in FULL_NAMES:
        return MONTHS[FULL_NAMES.index(raw)]
    return raw  # leave anything unrecognized (e.g. season names) untouched


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <bib_file> <doi>", file=sys.stderr)
        sys.exit(1)

    bib_path, doi = sys.argv[1], sys.argv[2]

    with open(bib_path, encoding="utf-8") as f:
        raw_text = f.read()

    parser = BibTexParser(common_strings=True)
    db = bibtexparser.loads(brace_bare_month_names(raw_text), parser=parser)

    if not db.entries:
        print(f"Warning: no entries parsed from {bib_path}", file=sys.stderr)
        return

    entry = db.entries[0]

    if entry.get("month"):
        entry["month"] = normalize_month(entry["month"])
    else:
        try:
            month = get_month_from_crossref(doi)
        except Exception as exc:
            print(f"Warning: could not query Crossref for {doi}: {exc}", file=sys.stderr)
            month = None

        if month:
            entry["month"] = month
            print(f"Backfilled month = {month} for {doi}")
        else:
            print(f"Note: Crossref has no month for {doi}", file=sys.stderr)

    writer = BibTexWriter()
    writer.indent = "    "
    writer.align_values = 14
    writer.display_order = FIELD_ORDER
    writer.add_trailing_comma = False

    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(writer.write(db))


if __name__ == "__main__":
    main()
