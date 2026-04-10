#!/usr/bin/env python3
"""Generate a print-ready PDF from index.html."""

from pathlib import Path
from playwright.sync_api import sync_playwright


HTML_INPUT = Path("index.html").resolve()
PDF_OUTPUT = Path("Wilhan_Nunes_CV.pdf")


def build_pdf() -> None:
    if not HTML_INPUT.exists():
        raise FileNotFoundError(f"Missing input HTML: {HTML_INPUT}")

    url = HTML_INPUT.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.emulate_media(media="print")
        page.pdf(
            path=str(PDF_OUTPUT),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()

    print(f"✓ Generated {PDF_OUTPUT}")


if __name__ == "__main__":
    build_pdf()
