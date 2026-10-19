# Wilhan Nunes — CV & Portfolio

Source for my academic CV website: **[wilhan-nunes.github.io](https://wilhan-nunes.github.io)**

## What's here

| Path | What it is |
|---|---|
| `content/cv.toml` | All hand-written CV content: profile, research, experience, education, skills |
| `publications/*.bib` | One BibTeX file per publication (source of truth for publications) |
| `templates/`, `static/style.css` | Jinja2 page templates and the shared stylesheet |
| `tools/*.html` | Self-contained single-file tools, listed automatically on `tools.html` |
| `build_site.py` | Renders `index.html`, `research.html`, `experience.html`, `publications.html`, `tools.html`, `cv.html` |
| `build_pdf.py` | Renders `cv.html` to `Wilhan_Nunes_CV.pdf` (headless Chromium) |
| `build_docx.py` | Writes an editable Word CV to `_private/Wilhan_Nunes_CV.docx` |

`_private/` is kept in the repository but is never published on the site (Jekyll skips
underscore paths, and `_config.yml` excludes it explicitly). The site doesn't link to it.

## Local setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Rebuilding

```bash
python build_site.py   # all HTML pages
python build_pdf.py    # Wilhan_Nunes_CV.pdf (from cv.html)
python build_docx.py   # _private/Wilhan_Nunes_CV.docx
```

CI (`.github/workflows/build.yml`) runs all three on every push to `main`, after fetching any
missing `.bib` files, and commits the results.

## Editing content

Edit `content/cv.toml` and push. Inline `<strong>`/`<em>` tags are allowed in text fields.
To change how your name is matched for bolding in author lists, edit `person.author_aliases`.

## Adding a publication

You can add a publication in any of three ways:

1. **Drop a `.bib` file** into `publications/` (one entry per file, named after the DOI with `/` → `_`) and push.
2. **Write the DOI** on a new line in `publications/doi_list.txt` and push. CI downloads the `.bib`.
3. **ORCID sync**: `.github/workflows/orcid-sync.yml` checks ORCID every Monday (or run it by hand from the
   Actions tab). New works are fetched into a pull request titled *New publications from ORCID*.
   - **Merge** the pull request to approve.
   - **Close** it to reject. `orcid-reject.yml` adds those DOIs to `publications/ignored_dois.txt` so they aren't suggested again.

   For ORCID sync to open pull requests, turn on *Settings → Actions → General → Allow GitHub Actions to create and approve pull requests*.

When a preprint is published, move its `.bib` and DOI to `publications/superseded_preprints/`.
The build ignores that folder, and ORCID sync won't suggest the preprint again.

You can also run the ORCID check locally:

```bash
python publications/fetch_orcid.py           # dry run: show new DOIs
python publications/fetch_orcid.py --write   # append them to doi_list.txt
python publications/fetch_orcid.py --fetch   # append + run fetch_bibs.sh
```

## Adding a tool

Put a self-contained `.html` file in `tools/`. Its `<title>` and
`<meta name="description" content="…">` become the card on the Tools page. The Tools page is marked `noindex`.
