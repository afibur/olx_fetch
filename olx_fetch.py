#!/usr/bin/env python3
"""Fetch long-term apartment rental listings on a given street in Kyiv from OLX.

Uses the public JSON endpoint the olx.ua web frontend itself calls
(https://www.olx.ua/api/v1/offers/). There is no official partner API for
this kind of ad-hoc search, so this mirrors what a browser sends. OLX does
not expose a street-level filter, so results are fetched for the whole
"long-term apartment rental / Kyiv" category and then filtered locally by
matching the street name against each offer's title/description/location.

Example:
    python olx_fetch.py --street "франка" --limit 200 --output data/franko_kyiv_rentals.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

import requests

API_URL = "https://www.olx.ua/api/v1/offers/"
CATEGORY_ID = 1307  # Довгострокова оренда квартир
CITY_NAME = "Київ"
PAGE_SIZE = 50
REQUEST_DELAY_S = 0.5  # be polite between paginated requests

HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (compatible; olx_fetch/1.0; "
        "+https://github.com/afibur/olx_fetch)"
    ),
}


@dataclass
class Listing:
    id: int
    title: str
    price: float | None
    currency: str | None
    city: str | None
    address: str | None
    district: str | None
    rooms: str | None
    area_m2: str | None
    floor: str | None
    url: str
    created_at: str | None
    photo_url: str | None


def iter_offers(session: requests.Session, city: str = CITY_NAME) -> Iterator[dict[str, Any]]:
    """Yield raw offer dicts for the rental category in `city`, paginated."""
    offset = 0
    while True:
        params = {
            "category_id": CATEGORY_ID,
            "region": "kyiv",
            "city": city,
            "currency": "UAH",
            "offset": offset,
            "limit": PAGE_SIZE,
            "sort_by": "created_at:desc",
        }
        resp = session.get(API_URL, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        offers = payload.get("data", [])
        if not offers:
            return
        yield from offers

        offset += PAGE_SIZE
        total = payload.get("metadata", {}).get("total_elements")
        if total is not None and offset >= total:
            return
        time.sleep(REQUEST_DELAY_S)


def _param(offer: dict[str, Any], key: str) -> str | None:
    for p in offer.get("params", []):
        if p.get("key") == key:
            value = p.get("value", {})
            return value.get("label") or value.get("key")
    return None


def _matches_street(offer: dict[str, Any], street: str) -> bool:
    needle = street.strip().lower()
    haystacks = [
        offer.get("title", ""),
        offer.get("description", ""),
        (offer.get("location") or {}).get("district", {}).get("name", ""),
    ]
    return any(needle in h.lower() for h in haystacks if h)


def to_listing(offer: dict[str, Any]) -> Listing:
    location = offer.get("location") or {}
    photos = offer.get("photos") or []
    return Listing(
        id=offer["id"],
        title=offer.get("title", ""),
        price=(offer.get("params") and _param(offer, "price")) or offer.get("price"),
        currency=(offer.get("price_label") or {}).get("currency"),
        city=location.get("city", {}).get("name"),
        address=location.get("address"),
        district=location.get("district", {}).get("name"),
        rooms=_param(offer, "rooms"),
        area_m2=_param(offer, "m"),
        floor=_param(offer, "floor"),
        url=offer.get("url", ""),
        created_at=offer.get("created_time"),
        photo_url=(photos[0].get("link") if photos else None),
    )


def fetch_street_listings(street: str, limit: int | None = None) -> list[Listing]:
    session = requests.Session()
    results: list[Listing] = []
    for offer in iter_offers(session):
        if _matches_street(offer, street):
            results.append(to_listing(offer))
            if limit and len(results) >= limit:
                break
    return results


def save_json(listings: list[Listing], path: Path) -> None:
    path.write_text(
        json.dumps([asdict(item) for item in listings], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_csv(listings: list[Listing], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(listings[0]).keys()) if listings else [])
        writer.writeheader()
        for item in listings:
            writer.writerow(asdict(item))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--street", default="франка", help="Street name to filter by (substring match).")
    parser.add_argument("--limit", type=int, default=None, help="Max number of matching listings to fetch.")
    parser.add_argument("--output", default="data/franko_kyiv_rentals.json", help="Output file (.json or .csv).")
    args = parser.parse_args()

    listings = fetch_street_listings(args.street, args.limit)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.suffix == ".csv":
        save_csv(listings, out_path)
    else:
        save_json(listings, out_path)

    print(f"Saved {len(listings)} listings to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
