# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is Wilhan Nunes's academic CV and personal portfolio as a static multipage website hosted on GitHub Pages (`wilhan-nunes.github.io`). Pages, a PDF and a Word CV are all generated from one content file (`content/cv.toml`) plus BibTeX publication files.

## Build Commands

```bash
python build_site.py   # render all HTML pages at the repo root
python build_pdf.py    # cv.html → Wilhan_Nunes_CV.pdf (Playwright + Chromium)
python build_docx.py   # → _private/Wilhan_Nunes_CV.docx (not published on the site)
```

**Dependencies** (Python 3.11+): `pip install -r requirements.txt && playwright install chromium`

## Architecture

### Content Flow

```
content/cv.toml ─┐
publications/*.bib ─┼─ sitegen.load_cv() ─┬─ build_site.py (templates/*.j2) → index, research, experience,
tools/*.html ────┘                     │                               publications, tools, cv .html
                                       ├─ build_pdf.py  (renders cv.html) → Wilhan_Nunes_CV.pdf
                                       └─ build_docx.py → _private/Wilhan_Nunes_CV.docx
```

### Key Files

- **`content/cv.toml`**: all hand-edited content. Inline `<strong>`/`<em>` allowed. `person.author_aliases` lists the name variants bolded in author lists.
- **`sitegen/`**: `load_cv()` loads the TOML and parses bibs. `pubs.py` classifies article vs. preprint, formats authors (truncated to 6, but always keeps the CV owner visible with "…"), and fills in preprint venues from the DOI prefix.
- **`templates/`**: Jinja2, `base.html.j2` + one template per page; shared pieces are in `macros.html.j2`. **`static/style.css`** is the only stylesheet (light/dark tokens on `:root`, print rules for the PDF).
- Generated `*.html` at the root are build outputs. Edit the templates or content instead.
- **`build_docx.py`**: python-docx; output is byte-reproducible (fixed zip timestamps) so CI doesn't commit it unless content changed.
- **`_private/`**: in the repo, never served (Jekyll ignores underscore paths; `_config.yml` also excludes build sources).
- **`tools/*.html`**: self-contained tools; `<title>` and `<meta name="description">` feed the Tools page cards.

### CI/CD

- `build.yml` runs on push to `main`. It fetches `.bib` files for DOIs in `doi_list.txt` that don't have one yet, builds the site, PDF and DOCX, and commits them with `[skip ci]`.
- `orcid-sync.yml` runs weekly and on manual dispatch. It runs `fetch_orcid.py --fetch` (ORCID + OpenAlex author `A5004018161`; optional `OPENALEX_API_KEY` secret) and opens or updates a PR on the `orcid-sync` branch. The PR is the approval step: merging approves.
- `orcid-reject.yml`: closing that PR unmerged appends its DOIs to `publications/ignored_dois.txt`.

## Adding Publications

Drop a `.bib` in `publications/`, or add a DOI to `publications/doi_list.txt`, or approve an ORCID sync PR. Required BibTeX fields: `author`, `title`, `year`. Recommended: `journal`/`publisher`, `volume`, `pages`, `doi`, `month`.

`publications/superseded_preprints/` holds preprints that were later published as articles. The build does not read it, so new preprints go directly in `publications/`. When a preprint is published, move its `.bib` and DOI there so ORCID sync doesn't report it again.

`python publications/fetch_orcid.py` queries ORCID and OpenAlex (OpenAlex results are filtered to article/preprint/review-like types, skipping Zenodo/figshare mirrors; each new DOI is tagged with its source). It is a dry run by default. `--write` appends new DOIs to `doi_list.txt`, and `--fetch` also runs `fetch_bibs.sh`. Known DOIs come from `doi_list.txt` files, `.bib` filenames in both folders, and `ignored_dois.txt`.
