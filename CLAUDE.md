# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is Wilhan Nunes's academic CV and personal portfolio as a static website hosted on GitHub Pages (`wilhan-nunes.github.io`). The site is built from BibTeX publication files and a hand-authored `index.html`, with Python scripts generating the publications section and PDF export.

## Build Commands

```bash
# Regenerate publications section in index.html and _publications.html
python build_publications.py

# Generate Wilhan_Nunes_CV.pdf from index.html (requires Playwright + Chromium)
python build_pdf.py
```

**Dependencies** (Python 3.11+):
```bash
pip install bibtexparser jinja2 playwright
playwright install chromium
```

## Architecture

### Content Flow

```
publications/*.bib  →  build_publications.py  →  index.html (injected between markers)
                                               →  _publications.html (standalone snippet)

index.html  →  build_pdf.py  →  Wilhan_Nunes_CV.pdf
```

### Key Files

- **`index.html`** — Single-page CV with all static content (bio, projects, experience, skills, education) and embedded CSS. The publications section is auto-generated; everything else is hand-edited here.
- **`build_publications.py`** — Parses all `.bib` files in `publications/`, classifies entries as articles vs. preprints, groups by year, renders via Jinja2, and injects between `<!-- PUB_START -->` and `<!-- PUB_END -->` markers in `index.html`.
- **`build_pdf.py`** — Uses Playwright (headless Chromium) to render `index.html` to A4 PDF with print media emulation.
- **`publications/*.bib`** — One BibTeX file per publication (the source of truth for publication data).

### CI/CD

GitHub Actions (`.github/workflows/build.yml`) runs on every push to `main`:
1. Runs `build_publications.py` and `build_pdf.py`
2. Commits any changed `index.html`, `_publications.html`, and `Wilhan_Nunes_CV.pdf` back to the repo with `[skip ci]` to avoid loops

Manual rebuilds can be triggered via `workflow_dispatch`.

## Adding Publications

Create a new `.bib` file in `publications/` with a single BibTeX entry, then run `python build_publications.py`. The script will:
- Auto-classify as **article** or **preprint** based on journal/publisher name (preprint detection checks for "biorxiv", "medrxiv", "chemrxiv", "preprint", "Research Square", etc.)
- Format authors as "Last F., Last F., ..." (truncated to "et al." for 6+ authors)
- Convert LaTeX markup (`\textit{}`, `\textbf{}`, braces) to HTML

Required BibTeX fields: `author`, `title`, `year`. Recommended: `journal`/`publisher`, `volume`, `pages`, `doi`, `month`.
