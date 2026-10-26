#!/usr/bin/env python3
"""
fetch_orcid.py [--orcid ID] [--openalex ID] [--write | --fetch]

Lists the works on an ORCID record (public API, no auth) and on an OpenAlex
author profile, and reports the DOIs that are not yet in this repo. Each new
DOI is tagged with the source(s) that listed it. OpenAlex profiles are built
automatically and can include misattributed works, so review those before adding.
Set OPENALEX_API_KEY to use your own OpenAlex quota (optional). Known DOIs come from doi_list.txt and
the existing .bib filenames, in both publications/ and publications/superseded_preprints/.
DOIs listed in publications/ignored_dois.txt (rejected suggestions) are skipped.

    (default)  dry run: only print what is new
    --write    append new DOIs to publications/doi_list.txt
    --fetch    --write, then run fetch_bibs.sh to download the .bib files
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_ORCID = "0000-0002-0609-6678"
DEFAULT_OPENALEX = "A5004018161"
SCRIPT_DIR = Path(__file__).resolve().parent
DOI_LIST = SCRIPT_DIR / "doi_list.txt"
KNOWN_DIRS = [SCRIPT_DIR, SCRIPT_DIR / "superseded_preprints"]
IGNORED = SCRIPT_DIR / "ignored_dois.txt"

# OpenAlex types worth suggesting; datasets, software, dissertations and errata are skipped
OPENALEX_TYPES = {"article", "preprint", "review", "letter", "book-chapter", "book"}
# Repository mirrors (Zenodo, figshare) of works that have a publisher DOI
MIRROR_PREFIXES = ("10.5281/", "10.6084/")

# bioRxiv (old + new prefix), ChemRxiv, Research Square
PREPRINT_PREFIXES = ("10.1101/", "10.64898/", "10.26434/", "10.21203/")


def normalize_doi(doi: str) -> str:
    doi = doi.strip().lower()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi


def match_key(doi: str) -> str:
    """Key used for comparisons: filename-style, without a trailing version
    suffix (bioRxiv DOIs are sometimes stored as ...714844v1)."""
    return re.sub(r"v\d+$", "", normalize_doi(doi).replace("/", "_"))


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "git-cv-build/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_orcid_works(orcid: str) -> list[dict]:
    data = get_json(f"https://pub.orcid.org/v3.0/{orcid}/works")

    works = []
    # ORCID groups duplicate records of the same work (e.g. from Crossref and
    # manual entry); one entry per group is enough.
    for group in data.get("group", []):
        summary = group["work-summary"][0]
        ids = group.get("external-ids", {}).get("external-id", [])
        doi = next((i["external-id-value"] for i in ids
                    if i.get("external-id-type") == "doi"), None)
        pub_date = summary.get("publication-date") or {}
        works.append({
            "doi":   normalize_doi(doi) if doi else None,
            "title": ((summary.get("title") or {}).get("title") or {}).get("value", ""),
            "year":  (pub_date.get("year") or {}).get("value", "????"),
            "type":  summary.get("type", ""),
        })
    return works


def fetch_openalex_works(author_id: str) -> list[dict]:
    params = {
        "filter": f"authorships.author.id:{author_id}",
        "select": "doi,title,publication_year,type",
        "per-page": "200",
        "cursor": "*",
    }
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]

    works = []
    while params["cursor"]:
        data = get_json("https://api.openalex.org/works?" + urllib.parse.urlencode(params))
        for w in data.get("results", []):
            if w.get("type") not in OPENALEX_TYPES:
                continue
            if w.get("doi") and normalize_doi(w["doi"]).startswith(MIRROR_PREFIXES):
                continue
            works.append({
                "doi":   normalize_doi(w["doi"]) if w.get("doi") else None,
                "title": w.get("title") or "",
                "year":  str(w.get("publication_year") or "????"),
                "type":  w.get("type") or "",
            })
        params["cursor"] = data.get("meta", {}).get("next_cursor")
    return works


def known_keys() -> set[str]:
    keys = set()
    for folder in KNOWN_DIRS:
        doi_list = folder / "doi_list.txt"
        if doi_list.exists():
            keys |= {match_key(l) for l in doi_list.read_text().splitlines() if l.strip()}
        keys |= {match_key(p.stem) for p in folder.glob("*.bib")}
    if IGNORED.exists():
        keys |= {match_key(l) for l in IGNORED.read_text().splitlines()
                 if l.strip() and not l.startswith("#")}
    return keys


def is_preprint(work: dict) -> bool:
    return work["type"] == "preprint" or work["doi"].startswith(PREPRINT_PREFIXES)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orcid", default=DEFAULT_ORCID)
    ap.add_argument("--openalex", default=DEFAULT_OPENALEX, help="OpenAlex author ID ('' to skip)")
    ap.add_argument("--write", action="store_true", help="append new DOIs to doi_list.txt")
    ap.add_argument("--fetch", action="store_true", help="--write, then run fetch_bibs.sh")
    args = ap.parse_args()

    sources = [("ORCID", args.orcid, fetch_orcid_works)]
    if args.openalex:
        sources.append(("OpenAlex", args.openalex, fetch_openalex_works))

    known = known_keys()
    new: dict[str, dict] = {}   # match_key -> work, with the sources that list it
    no_doi = []
    for name, ident, fetch in sources:
        try:
            works = fetch(ident)
        except OSError as e:     # one source being down shouldn't block the other
            print(f"! {name} {ident}: request failed ({e})", file=sys.stderr)
            continue
        found = 0
        for w in works:
            if not w["doi"]:
                # OpenAlex lists many DOI-less records (theses, duplicates); only ORCID's are worth a look
                if name == "ORCID":
                    no_doi.append(w)
                continue
            key = match_key(w["doi"])
            if key in known:
                continue
            if key not in new:
                new[key] = {**w, "sources": []}
                found += 1
            if name not in new[key]["sources"]:
                new[key]["sources"].append(name)
        print(f"{name} {ident}: {len(works)} works, {found} new DOI(s)")

    new = sorted(new.values(), key=lambda w: w["year"], reverse=True)
    print(f"\n{len(new)} new DOI(s) in total")
    for w in new:
        tag = " [preprint]" if is_preprint(w) else ""
        print(f"  + {w['doi']}  ({w['year']}){tag}  [{', '.join(w['sources'])}]\n      {w['title']}")

    if no_doi:
        print(f"\n{len(no_doi)} ORCID work(s) without a DOI (add manually if needed):")
        for w in no_doi:
            print(f"  ? ({w['year']}, {w['type']}) {w['title']}")

    if not new or not (args.write or args.fetch):
        if new:
            print("\nDry run. Use --write to append to doi_list.txt, or --fetch to also download .bib files.")
        return

    text = DOI_LIST.read_text() if DOI_LIST.exists() else ""
    if text and not text.endswith("\n"):
        text += "\n"
    DOI_LIST.write_text(text + "".join(f"{w['doi']}\n" for w in new))
    print(f"\n✓ Appended {len(new)} DOI(s) to {DOI_LIST.relative_to(SCRIPT_DIR.parent)}")

    if args.fetch:
        result = subprocess.run(["bash", str(SCRIPT_DIR / "fetch_bibs.sh"), str(DOI_LIST)])
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
