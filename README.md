# Wilhan Nunes — CV & Portfolio

Source for my academic CV website: **[wilhan-nunes.github.io](https://wilhan-nunes.github.io)**

## What's here

- `index.html` — Single-page CV (bio, projects, experience, skills, education)
- `publications/*.bib` — One BibTeX file per publication (source of truth)
- `build_publications.py` — Parses BibTeX files and injects the publications section into `index.html`
- `build_pdf.py` — Renders `index.html` to `Wilhan_Nunes_CV.pdf` via headless Chromium

## Local setup

```bash
pip install "bibtexparser<2" jinja2 playwright
playwright install chromium
```

## Rebuilding

```bash
python build_publications.py   # update publications in index.html
python build_pdf.py            # regenerate PDF
```

CI runs both automatically on every push to `main` and commits the updated files.

## Adding a publication

1. Add the new DOI to `publications/doi_list.txt`
2. Run `bash publications/fetch_bibs.sh publications/doi_list.txt` locally — fetches and formats the `.bib` file
3. Commit and push the new `.bib` file and updated `doi_list.txt`
4. CI automatically runs `build_publications.py` and `build_pdf.py`, and commits the updated `index.html` and PDF back to the repo

### Syncing from ORCID

`publications/fetch_orcid.py` lists the works on the ORCID record and reports DOIs not yet in the repo (checks `publications/` and `publications/preprints/`):

```bash
python publications/fetch_orcid.py           # dry run: show new DOIs
python publications/fetch_orcid.py --write   # append them to doi_list.txt
python publications/fetch_orcid.py --fetch   # append + run fetch_bibs.sh
```

Preprints are tagged `[preprint]`. Review them before fetching, since a preprint may already be in the CV as its published version.
