"""Parse publications/*.bib into plain dicts shared by the site, PDF and DOCX builds."""

import html
import re
from itertools import groupby
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

PREPRINT_SERVERS = {"chemrxiv", "biorxiv", "medrxiv", "research square", "arxiv", "openrxiv"}

# Venue to show when a preprint's .bib has no journal field (common for
# openRxiv / Research Square DOIs), keyed by DOI prefix.
PREPRINT_VENUES = {
    "10.1101/": "bioRxiv",
    "10.64898/": "bioRxiv",
    "10.26434/": "ChemRxiv",
    "10.21203/": "Research Square",
}

MAX_AUTHORS = 6

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def clean_latex(text: str) -> str:
    """Strip basic LaTeX markup, converting \\textit/\\textbf to HTML."""
    # Handle both \textit{word} and \textitword (after brace stripping)
    text = re.sub(r"\\textit\{([^}]+)\}", r"<em>\1</em>", text)
    text = re.sub(r"\\textit(\w+)", r"<em>\1</em>", text)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"<strong>\1</strong>", text)
    text = re.sub(r"\\textbf(\w+)", r"<strong>\1</strong>", text)
    text = re.sub(r"\{([^}]*)\}", r"\1", text)   # remove remaining braces
    text = html.unescape(text.replace("\\&", "&")).replace("--", "–")
    return re.sub(r"\s+", " ", text).strip()


def short_author(raw: str) -> str:
    """'Last, First Middle' → 'Last F.M.'"""
    if "," not in raw:
        return raw.strip()
    last, first = (p.strip() for p in raw.split(",", 1))
    initials = "".join(w[0] + "." for w in re.split(r"[\s-]+", first) if w)
    return f"{last} {initials}"


def parse_month(raw_month: str) -> int:
    """Convert BibTeX month field to month number (1-12), defaulting to 0."""
    text = clean_latex(str(raw_month or "")).lower()
    if text in MONTHS:
        return MONTHS[text]
    m = re.search(r"\d+", text)
    return int(m.group()) if m and 1 <= int(m.group()) <= 12 else 0


def author_list(authors: list[str], aliases: set[str]) -> list[dict]:
    """Truncate to MAX_AUTHORS, keeping the CV owner visible.

    Returns [{"name": str, "me": bool}] with an {"ellipsis": True} marker where
    authors were skipped and {"etal": True} when the list was cut short.
    """
    marked = [{"name": a, "me": a in aliases} for a in authors]
    if len(marked) <= MAX_AUTHORS:
        return marked
    me_idx = next((i for i, a in enumerate(marked) if a["me"]), None)
    if me_idx is None or me_idx < MAX_AUTHORS:
        return marked[:MAX_AUTHORS] + [{"etal": True}]
    # Owner is deep in the list: show the first authors, then the owner.
    out = marked[:MAX_AUTHORS - 2] + [{"ellipsis": True}, marked[me_idx]]
    if me_idx < len(marked) - 1:
        out.append({"etal": True})
    return out


def parse_bibs(folder: str | Path, aliases: list[str]) -> list[dict]:
    alias_set = set(aliases)
    entries = []
    for bib_file in sorted(Path(folder).glob("*.bib")):
        parser = BibTexParser()
        parser.customization = convert_to_unicode
        text = bib_file.read_text(encoding="utf-8")
        # doi.org writes months as bare macros (month=Sept); anything other than
        # the standard jan..dec is an undefined string to bibtexparser, so brace it.
        text = re.sub(r"(\bmonth\s*=\s*)([A-Za-z]+)", r"\1{\2}", text, flags=re.I)
        db = bibtexparser.loads(text, parser=parser)
        for e in db.entries:
            doi = e.get("doi", "").strip()
            journal = clean_latex(e.get("journal", e.get("booktitle", "")))
            source = f"{journal} {e.get('publisher', '')}".lower()
            pub_type = "preprint" if any(s in source for s in PREPRINT_SERVERS) else "article"
            if not journal and pub_type == "preprint":
                journal = next((v for p, v in PREPRINT_VENUES.items() if doi.startswith(p)),
                               clean_latex(e.get("publisher", "")))
            authors = [short_author(a) for a in clean_latex(e.get("author", "")).split(" and ") if a.strip()]
            entries.append({
                "key":     bib_file.stem,
                "type":    pub_type,
                "year":    int(e.get("year", 0)),
                "month":   parse_month(e.get("month", "")),
                "authors": author_list(authors, alias_set),
                "first_author": bool(authors) and authors[0] in alias_set,
                "title":   clean_latex(e.get("title", "")).rstrip("."),
                "journal": journal,
                "volume":  e.get("volume", "").strip(),
                "pages":   clean_latex(e.get("pages", "")),
                "doi":     doi,
            })
    return sorted(entries, key=lambda x: (x["year"], x["month"]), reverse=True)


def group_by_year(entries: list[dict]) -> list[tuple[int, list[dict]]]:
    return [(year, list(group)) for year, group in groupby(entries, key=lambda x: x["year"])]
