"""Shared client for the public OLX.ua JSON search API.

This is the same endpoint the olx.ua web frontend calls
(https://www.olx.ua/api/v1/offers/); there is no official partner API for
ad-hoc searches like this, so requests mirror what a browser sends.

Two search modes are supported, matching what the site itself offers:
  * `iter_category_offers` — page through one category (e.g. "long-term
    apartment rentals"), for when you want to filter every listing in a
    category locally (used by olx_fetch.py for the street-name filter).
  * `iter_search_offers` — full-text search via the `q` parameter across
    OLX, with an optional category, for when the thing you're looking for
    (a product model, say) can appear across many categories.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterator

import requests

API_URL = "https://www.olx.ua/api/v1/offers/"
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
    id: str
    title: str
    price: float | None
    currency: str | None
    city: str | None
    district: str | None
    tags: list[str]
    description: str
    url: str
    created_at: str | None
    photo_url: str | None


def _paged_get(session: requests.Session, params: dict[str, Any]) -> Iterator[dict[str, Any]]:
    offset = 0
    while True:
        page_params = {**params, "offset": offset, "limit": PAGE_SIZE}
        resp = session.get(API_URL, headers=HEADERS, params=page_params, timeout=20)
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


def iter_category_offers(
    session: requests.Session, category_id: int, city: str | None = None
) -> Iterator[dict[str, Any]]:
    """Page through every offer in one category (optionally scoped to a city)."""
    params: dict[str, Any] = {
        "category_id": category_id,
        "currency": "UAH",
        "sort_by": "created_at:desc",
    }
    if city:
        params["city"] = city
        params["region"] = "kyiv"
    yield from _paged_get(session, params)


def iter_search_offers(
    session: requests.Session, query: str, category_id: int | None = None
) -> Iterator[dict[str, Any]]:
    """Page through full-text search results for `query`, optionally within a category."""
    params: dict[str, Any] = {
        "q": query,
        "currency": "UAH",
        "sort_by": "created_at:desc",
    }
    if category_id:
        params["category_id"] = category_id
    yield from _paged_get(session, params)


def _price(offer: dict[str, Any]) -> float | None:
    for p in offer.get("params", []):
        if p.get("key") == "price":
            return (p.get("value") or {}).get("value") or offer.get("price")
    return offer.get("price")


def extract_tags(offer: dict[str, Any]) -> list[str]:
    """Generic per-offer attributes (rooms/area/floor, or storage/RAM/condition,
    whatever the category has) as short display tags, price excluded."""
    tags = []
    for p in offer.get("params", []):
        if p.get("key") == "price":
            continue
        label = (p.get("value") or {}).get("label")
        if label:
            tags.append(label)
    return tags


def to_listing(offer: dict[str, Any]) -> Listing:
    location = offer.get("location") or {}
    photos = offer.get("photos") or []
    return Listing(
        id=str(offer["id"]),
        title=offer.get("title", ""),
        price=_price(offer),
        currency=(offer.get("price_label") or {}).get("currency"),
        city=location.get("city", {}).get("name"),
        district=location.get("district", {}).get("name"),
        tags=extract_tags(offer),
        description=offer.get("description", ""),
        url=offer.get("url", ""),
        created_at=offer.get("created_time"),
        photo_url=(photos[0].get("link") if photos else None),
    )


def text_matches(offer: dict[str, Any], needle: str) -> bool:
    needle = needle.strip().lower()
    haystacks = [
        offer.get("title", ""),
        offer.get("description", ""),
        (offer.get("location") or {}).get("district", {}).get("name", ""),
    ]
    return any(needle in h.lower() for h in haystacks if h)
