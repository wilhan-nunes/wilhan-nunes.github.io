#!/usr/bin/env python3
"""
build_publications.py
Reads all .bib files in the /publications folder and generates
a publications HTML snippet that gets injected into index.html.

Usage:
    python build_publications.py

Output:
    _publications.html  (injected into index.html between <!-- PUB_START --> and <!-- PUB_END -->)
"""

import re
import glob
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from jinja2 import Environment, BaseLoader
from pathlib import Path

# ── Jinja2 template for the publications section ──────────────────────────────
TEMPLATE = """
{%- for year, entries in pubs_by_year %}
<div class="pub-year-group">
  <span class="pub-year">{{ year }}</span>
  <div class="pub-list">
  {%- for entry in entries %}
    <div class="pub-entry {{ entry.type }}">
      <p class="pub-authors">{{ entry.authors }}</p>
      <p class="pub-title">{{ entry.title }}
        {%- if entry.type == 'preprint' %} <span class="badge">Preprint</span>{%- endif %}
      </p>
      <p class="pub-venue">
        <em>{{ entry.journal }}</em>
        {%- if entry.volume %}, v.{{ entry.volume }}{%- endif %}
        {%- if entry.pages %}, p. {{ entry.pages }}{%- endif %}.
        {%- if entry.doi %}
        <a href="https://doi.org/{{ entry.doi }}" target="_blank" rel="noopener">DOI ↗</a>
        {%- endif %}
      </p>
    </div>
  {%- endfor %}
  </div>
</div>
{%- endfor %}
"""

def clean_latex(text: str) -> str:
    """Strip basic LaTeX markup."""
    # Handle both \textit{word} and \textitword (after brace stripping)
    text = re.sub(r"\\textit\{([^}]+)\}", r"<em>\1</em>", text)
    text = re.sub(r"\\textit(\w+)", r"<em>\1</em>", text)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"<strong>\1</strong>", text)
    text = re.sub(r"\\textbf(\w+)", r"<strong>\1</strong>", text)
    text = re.sub(r"\{([^}]*)\}", r"\1", text)   # remove remaining braces
    text = text.replace("\\&", "&").replace("--", "–")
    return text.strip()

def format_authors(raw: str) -> str:
    """Convert 'Last, First and Last, First' → 'Last F., Last F., ...'"""
    authors = [a.strip() for a in raw.split(" and ")]
    short = []
    for a in authors:
        if "," in a:
            parts = a.split(",", 1)
            last = parts[0].strip()
            first = parts[1].strip()
            initials = "".join(w[0] + "." for w in first.split() if w)
            short.append(f"{last} {initials}")
        else:
            short.append(a)
    if len(short) > 6:
        return ", ".join(short[:6]) + " et al."
    return ", ".join(short)

def parse_bibs(folder: str = "publications") -> list[dict]:
    entries = []
    parser = BibTexParser()
    parser.customization = convert_to_unicode

    for bib_file in glob.glob(f"{folder}/*.bib"):
        with open(bib_file, encoding="utf-8") as f:
            db = bibtexparser.load(f, parser=parser)
        for e in db.entries:
            entry_type = e.get("ENTRYTYPE", "article").lower()
            pub_type = "preprint" if entry_type == "preprint" else "article"
            entries.append({
                "type":    pub_type,
                "year":    int(e.get("year", 0)),
                "authors": format_authors(clean_latex(e.get("author", ""))),
                "title":   clean_latex(e.get("title", "")),
                "journal": clean_latex(e.get("journal", e.get("booktitle", ""))),
                "volume":  e.get("volume", ""),
                "pages":   clean_latex(e.get("pages", "")),
                "doi":     e.get("doi", "").strip(),
            })

    return sorted(entries, key=lambda x: -x["year"])

def group_by_year(entries: list[dict]):
    from itertools import groupby
    result = []
    for year, group in groupby(entries, key=lambda x: x["year"]):
        result.append((year, list(group)))
    return result

def render(entries: list[dict]) -> str:
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(TEMPLATE)
    return tmpl.render(pubs_by_year=group_by_year(entries))

def inject_into_index(html_snippet: str, index_path: str = "index.html"):
    """Replace content between <!-- PUB_START --> and <!-- PUB_END --> in index.html."""
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(<!-- PUB_START -->).*?(<!-- PUB_END -->)"
    replacement = r"\g<1>\n" + html_snippet + "\n\\g<2>"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✓ Injected {len(entries)} publications into {index_path}")

if __name__ == "__main__":
    entries = parse_bibs("publications")
    html_snippet = render(entries)

    # Save standalone snippet
    Path("_publications.html").write_text(html_snippet, encoding="utf-8")
    print(f"✓ Generated _publications.html ({len(entries)} entries)")

    # Inject into index.html if it exists
    if Path("index.html").exists():
        inject_into_index(html_snippet)
