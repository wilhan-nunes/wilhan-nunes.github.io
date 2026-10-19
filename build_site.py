#!/usr/bin/env python3
"""
build_site.py
Renders the multipage site from content/cv.toml, publications/*.bib and
tools/*.html, using the Jinja2 templates in templates/.

Usage:
    python build_site.py

Output (repo root, served by GitHub Pages):
    index.html, research.html, experience.html, publications.html,
    tools.html, cv.html (cv.html is also the source of the PDF)
"""

import datetime as dt
import html
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from sitegen import ROOT, load_cv

# (output slug, nav label, page title)
PAGES = [
    ("index",        "About",        None),
    ("research",     "Research",     "Research"),
    ("experience",   "Experience",   "Experience"),
    ("publications", "Publications", "Publications"),
    ("tools",        "Tools",        "Tools"),
    ("cv",           "CV",           "Curriculum Vitae"),
]


def scan_tools(folder: Path) -> list[dict]:
    """Collect title and description from each self-contained tools/*.html."""
    tools = []
    for f in sorted(folder.glob("*.html")):
        text = f.read_text(encoding="utf-8", errors="replace")
        title = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
        desc = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', text, re.S | re.I)
        tools.append({
            "file": f.name,
            "title": html.unescape(title.group(1).strip()) if title else f.stem.replace("-", " ").title(),
            "description": html.unescape(desc.group(1).strip()) if desc else "",
        })
    return tools


def main() -> None:
    cv = load_cv()
    env = Environment(loader=FileSystemLoader(ROOT / "templates"),
                      trim_blocks=False, lstrip_blocks=False, keep_trailing_newline=True)
    context = {
        **cv,
        # education/skills clash with macro names inside templates
        "cv_education": cv["education"],
        "cv_skills": cv["skills"],
        "tools": scan_tools(ROOT / "tools"),
        "nav": [(slug, label) for slug, label, _ in PAGES],
        "root": "",
        "year": dt.date.today().year,
    }
    for slug, _, title in PAGES:
        out = env.get_template(f"{slug}.html.j2").render(
            **context, page=slug, page_title=title,
            noindex=slug == "tools",
        )
        (ROOT / f"{slug}.html").write_text(out, encoding="utf-8")
        print(f"✓ Generated {slug}.html")
    print(f"  {len(cv['publications'])} publications, {len(context['tools'])} tool(s)")


if __name__ == "__main__":
    main()
