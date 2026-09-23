#!/usr/bin/env python3
"""
fetch_orcid.py [--orcid ID] [--write | --fetch]

Lists the works on an ORCID record (public API, no auth) and reports the
DOIs that are not yet in this repo. Known DOIs come from doi_list.txt and
the existing .bib filenames, in both publications/ and publications/preprints/.

    (default)  dry run: only print what is new
    --write    append new DOIs to publications/doi_list.txt
    --fetch    --write, then run fetch_bibs.sh to download the .bib files
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

DEFAULT_ORCID = "0000-0002-0609-6678"
SCRIPT_DIR = Path(__file__).resolve().parent
DOI_LIST = SCRIPT_DIR / "doi_list.txt"
KNOWN_DIRS = [SCRIPT_DIR, SCRIPT_DIR / "preprints"]

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


def fetch_works(orcid: str) -> list[dict]:
    url = f"https://pub.orcid.org/v3.0/{orcid}/works"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "git-cv-build/1.0",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)

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


def known_keys() -> set[str]:
    keys = set()
    for folder in KNOWN_DIRS:
        doi_list = folder / "doi_list.txt"
        if doi_list.exists():
            keys |= {match_key(l) for l in doi_list.read_text().splitlines() if l.strip()}
        keys |= {match_key(p.stem) for p in folder.glob("*.bib")}
    return keys


def is_preprint(work: dict) -> bool:
    return work["type"] == "preprint" or work["doi"].startswith(PREPRINT_PREFIXES)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orcid", default=DEFAULT_ORCID)
    ap.add_argument("--write", action="store_true", help="append new DOIs to doi_list.txt")
    ap.add_argument("--fetch", action="store_true", help="--write, then run fetch_bibs.sh")
    args = ap.parse_args()

    works = fetch_works(args.orcid)
    known = known_keys()

    new, no_doi, seen = [], [], set()
    for w in works:
        if not w["doi"]:
            no_doi.append(w)
        elif match_key(w["doi"]) not in known and w["doi"] not in seen:
            seen.add(w["doi"])
            new.append(w)

    print(f"ORCID {args.orcid}: {len(works)} works, {len(new)} new DOI(s)")
    for w in sorted(new, key=lambda w: w["year"], reverse=True):
        tag = " [preprint]" if is_preprint(w) else ""
        print(f"  + {w['doi']}  ({w['year']}){tag}\n      {w['title']}")

    if no_doi:
        print(f"\n{len(no_doi)} work(s) without a DOI (add manually if needed):")
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
