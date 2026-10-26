"""Shared loaders for build_site.py, build_pdf.py and build_docx.py."""

import tomllib
from pathlib import Path

from .pubs import group_by_year, parse_bibs

ROOT = Path(__file__).resolve().parent.parent


def load_cv() -> dict:
    """Return the CV content plus parsed publications."""
    cv = tomllib.loads((ROOT / "content" / "cv.toml").read_text(encoding="utf-8"))
    cv["summary"]["text"] = " ".join(cv["summary"]["text"].split())
    pubs = parse_bibs(ROOT / "publications", cv["person"]["author_aliases"])
    cv["publications"] = pubs
    cv["pubs_by_year"] = group_by_year(pubs)
    cv["pub_counts"] = {
        "article": sum(p["type"] == "article" for p in pubs),
        "preprint": sum(p["type"] == "preprint" for p in pubs),
        "first_author": sum(p["first_author"] for p in pubs),
    }
    return cv
