#!/usr/bin/env python3
"""Fetch OLX listings for Apple devices on Apple Silicon (M1-M5): MacBook
Air/Pro, Mac mini, iMac, Mac Studio, Mac Pro, iPad Pro.

OLX's full-text search (`q`) is run once per product line (MacBook, Mac
mini, iMac, ...) rather than restricted to one category, since these
devices are listed under different categories depending on the seller.
Results are pooled, de-duplicated by listing id, and kept only if the
title or description actually names an M1-M5 chip — this is what excludes
older Intel-based MacBooks/iMacs, which OLX has plenty of.

Example:
    python olx_fetch_apple_silicon.py --limit 200 --output data/apple_m_series.json
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests

from olx_api import Listing, iter_search_offers, to_listing
from olx_io import save_listings

PRODUCT_QUERIES = ["MacBook", "Mac mini", "iMac", "Mac Studio", "Mac Pro", "iPad Pro"]

# Matches "M1", "M2 Pro", "M3 Max", "M4 Ultra", ... as a whole word so it
# doesn't false-positive on unrelated model numbers.
CHIP_RE = re.compile(r"\bm[1-5](\s?(pro|max|ultra))?\b", re.IGNORECASE)


def _chip_matches(offer: dict) -> bool:
    haystack = f"{offer.get('title', '')} {offer.get('description', '')}"
    return bool(CHIP_RE.search(haystack))


def fetch_apple_silicon_listings(limit: int | None = None) -> list[Listing]:
    session = requests.Session()
    seen: dict[str, Listing] = {}
    for query in PRODUCT_QUERIES:
        for offer in iter_search_offers(session, query):
            if str(offer["id"]) in seen:
                continue
            if _chip_matches(offer):
                seen[str(offer["id"])] = to_listing(offer)
                if limit and len(seen) >= limit:
                    return list(seen.values())
    return list(seen.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="Max number of matching listings to fetch.")
    parser.add_argument("--output", default="data/apple_m_series.json", help="Output file (.json or .csv).")
    args = parser.parse_args()

    listings = fetch_apple_silicon_listings(args.limit)
    out_path = Path(args.output)
    query = {
        "street": None,
        "title": "Apple на M1-M5",
        "category": "MacBook, Mac mini, iMac, Mac Studio, Mac Pro, iPad Pro (Apple Silicon)",
    }
    save_listings(listings, out_path, query=query)

    print(f"Saved {len(listings)} listings to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
