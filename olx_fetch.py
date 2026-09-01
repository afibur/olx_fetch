#!/usr/bin/env python3
"""Fetch long-term apartment rental listings on a given street in Kyiv from OLX.

OLX does not expose a street-level filter, so this pages through the whole
"long-term apartment rental / Kyiv" category and filters locally by matching
the street name against each offer's title/description/district.

Example:
    python olx_fetch.py --street "франка" --limit 200 --output data/franko_kyiv_rentals.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from olx_api import Listing, iter_category_offers, text_matches, to_listing
from olx_io import save_listings

CATEGORY_ID = 1307  # Довгострокова оренда квартир
CITY_NAME = "Київ"


def fetch_street_listings(street: str, limit: int | None = None) -> list[Listing]:
    session = requests.Session()
    results: list[Listing] = []
    for offer in iter_category_offers(session, CATEGORY_ID, city=CITY_NAME):
        if text_matches(offer, street):
            results.append(to_listing(offer))
            if limit and len(results) >= limit:
                break
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--street", default="франка", help="Street name to filter by (substring match).")
    parser.add_argument("--limit", type=int, default=None, help="Max number of matching listings to fetch.")
    parser.add_argument("--output", default="data/franko_kyiv_rentals.json", help="Output file (.json or .csv).")
    args = parser.parse_args()

    listings = fetch_street_listings(args.street, args.limit)
    out_path = Path(args.output)
    query = {"street": args.street, "city": CITY_NAME, "category": "Довгострокова оренда квартир"}
    save_listings(listings, out_path, query=query)

    print(f"Saved {len(listings)} listings to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
