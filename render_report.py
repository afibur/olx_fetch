#!/usr/bin/env python3
"""Render fetched OLX listings (rentals, devices, anything with the shared
Listing shape) as a single self-contained, mobile-friendly HTML report —
readable in any browser, including Mobile Safari on iOS, with no app
required.

Accepts either the flat list produced by `olx_fetch*.py --output ....json`,
or a `{"query": ..., "source_note": ..., "listings": [...]}` wrapper (used
for the checked-in sample data). `query.street` selects the rental-report
styling (Golden Gate icon, "аренда на <street>" heading); its absence falls
back to a generic OLX-listings styling (chip icon), titled from
`query.title`/`query.subtitle`/`query.category` when present.

Example:
    python render_report.py data/franko_kyiv_rentals.json report.html
    python render_report.py data/apple_m_series.json apple_report.html
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

PAGE_TEMPLATE = """<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Manrope:wght@400;500;700&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #F3F1EC;
    --surface: #FFFDF9;
    --surface-2: #EAE5D8;
    --text: #24211B;
    --text-dim: #6C6558;
    --border: #DFDACB;
    --accent: #A6752B;
    --accent-strong: #7C5620;
    --accent-soft: #F1E4C8;
    --shadow: 0 1px 2px rgba(36, 33, 27, 0.06), 0 8px 20px -12px rgba(36, 33, 27, 0.18);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #1A1712;
      --surface: #221E17;
      --surface-2: #2C271D;
      --text: #F1ECE0;
      --text-dim: #B3AA96;
      --border: #3A3226;
      --accent: #DDAD53;
      --accent-strong: #F0C572;
      --accent-soft: #362A17;
      --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 8px 24px -12px rgba(0, 0, 0, 0.5);
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #1A1712;
    --surface: #221E17;
    --surface-2: #2C271D;
    --text: #F1ECE0;
    --text-dim: #B3AA96;
    --border: #3A3226;
    --accent: #DDAD53;
    --accent-strong: #F0C572;
    --accent-soft: #362A17;
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 8px 24px -12px rgba(0, 0, 0, 0.5);
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: "Manrope", system-ui, -apple-system, "Helvetica Neue", sans-serif;
    -webkit-font-smoothing: antialiased;
    padding: 28px 18px 64px;
  }}
  .page {{
    max-width: 640px;
    margin: 0 auto;
  }}
  .icon {{
    display: block;
    margin: 0 auto 18px;
    color: var(--accent);
  }}
  header {{
    text-align: center;
    margin-bottom: 22px;
  }}
  .eyebrow {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.72rem;
    letter-spacing: 0.11em;
    text-transform: uppercase;
    color: var(--accent-strong);
    margin: 0 0 10px;
  }}
  h1 {{
    font-family: "Fraunces", Georgia, serif;
    font-weight: 600;
    font-size: clamp(1.7rem, 6vw, 2.3rem);
    line-height: 1.12;
    margin: 0 0 10px;
    text-wrap: balance;
  }}
  .subtitle {{
    color: var(--text-dim);
    font-size: 0.95rem;
    line-height: 1.5;
    margin: 0;
  }}
  .stats {{
    display: flex;
    justify-content: center;
    gap: 22px;
    margin-top: 18px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
  }}
  .stat b {{
    display: block;
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
    font-size: 1.15rem;
    color: var(--text);
  }}
  .stat span {{
    font-size: 0.72rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }}

  .notice {{
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    font-size: 0.85rem;
    line-height: 1.55;
    color: var(--text-dim);
    margin: 22px 0 28px;
  }}
  .notice strong {{ color: var(--text); }}

  .listings {{
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 18px 16px;
    box-shadow: var(--shadow);
  }}
  .card-top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
  }}
  .card-title {{
    font-family: "Fraunces", Georgia, serif;
    font-weight: 600;
    font-size: 1.08rem;
    line-height: 1.3;
    margin: 0 0 4px;
  }}
  .card-district {{
    font-size: 0.83rem;
    color: var(--text-dim);
  }}
  .price {{
    font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
    font-size: 1.15rem;
    color: var(--accent-strong);
    white-space: nowrap;
  }}
  .meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 12px 0;
  }}
  .meta span {{
    background: var(--accent-soft);
    color: var(--accent-strong);
    font-size: 0.76rem;
    font-weight: 500;
    padding: 4px 9px;
    border-radius: 999px;
  }}
  .desc {{
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--text-dim);
    margin: 0 0 14px;
  }}
  .card a.cta {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.86rem;
    font-weight: 700;
    color: var(--accent-strong);
    text-decoration: none;
    border-bottom: 1px solid var(--accent);
    padding-bottom: 1px;
  }}
  .card a.cta:focus-visible, a:focus-visible {{
    outline: 2px solid var(--accent);
    outline-offset: 3px;
  }}

  .empty {{
    text-align: center;
    color: var(--text-dim);
    padding: 40px 20px;
    font-size: 0.95rem;
  }}

  footer {{
    text-align: center;
    margin-top: 34px;
    font-size: 0.78rem;
    color: var(--text-dim);
  }}
</style>

<div class="page">
  <header>
    {icon}
    <p class="eyebrow">{eyebrow}</p>
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
    <div class="stats">
      <div class="stat"><b>{count}</b><span>оголошень</span></div>
      <div class="stat"><b>{generated_at}</b><span>сформовано</span></div>
    </div>
  </header>

  {notice}

  <div class="listings">
    {cards}
  </div>

  <footer>Ціни та наявність можуть змінитися — перевіряйте оголошення за посиланням.</footer>
</div>
"""

CARD_TEMPLATE = """<article class="card">
      <div class="card-top">
        <div>
          <p class="card-title">{title}</p>
          <p class="card-district">{district}</p>
        </div>
        <p class="price">{price}</p>
      </div>
      <div class="meta">{meta}</div>
      <p class="desc">{description}</p>
      <a class="cta" href="{url}" target="_blank" rel="noopener">Переглянути на OLX &rarr;</a>
    </article>"""

EMPTY_TEMPLATE = '<p class="empty">Оголошень за цим фільтром поки не знайдено.</p>'

# A thin-line Golden Gate (Золоті Ворота) arch — used for the Kyiv rental
# report, whose sample listings all sit a few minutes from the landmark.
ICON_GATE = (
    '<svg class="icon" width="72" height="46" viewBox="0 0 72 46" fill="none" aria-hidden="true">'
    '<path d="M4 44V20C4 10 12 3 22 3M68 44V20C68 10 60 3 50 3M22 3C22 12 22 18 22 22'
    'M50 3C50 12 50 18 50 22M22 22C22 30 28 34 36 34C44 34 50 30 50 22M4 44H68" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
)

# A thin-line microchip — used for device/electronics reports.
ICON_CHIP = (
    '<svg class="icon" width="46" height="46" viewBox="0 0 46 46" fill="none" aria-hidden="true">'
    '<rect x="12" y="12" width="22" height="22" rx="3" stroke="currentColor" stroke-width="2"/>'
    '<rect x="19" y="19" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.6"/>'
    '<path d="M18 12V4M28 12V4M18 42V34M28 42V34M12 18H4M12 28H4M42 18H34M42 28H34" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
)


def _load(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return {"query": {}, "source_note": None, "listings": raw}
    raw.setdefault("listings", [])
    return raw


def _format_price(listing: dict[str, Any]) -> str:
    price = listing.get("price")
    currency = listing.get("currency") or ""
    if price is None:
        return "ціна не вказана"
    symbol = {"USD": "$", "UAH": "₴", "EUR": "€"}.get(currency, currency)
    try:
        price_str = f"{int(price):,}".replace(",", " ")
    except (TypeError, ValueError):
        price_str = str(price)
    return f"{symbol}{price_str}" if symbol in ("$", "€") else f"{price_str} {symbol}".strip()


def _meta_bits(listing: dict[str, Any]) -> list[str]:
    if listing.get("tags"):
        return list(listing["tags"])
    # Older data files (pre-refactor rental sample) used fixed keys instead
    # of a generic tag list — still render those.
    return [
        b
        for b in (listing.get("rooms"), listing.get("area_m2"), listing.get("floor"), listing.get("building"))
        if b
    ]


def _render_card(listing: dict[str, Any]) -> str:
    meta_html = "".join(f"<span>{html.escape(str(b))}</span>" for b in _meta_bits(listing))
    location = listing.get("district") or listing.get("city") or listing.get("address") or ""
    return CARD_TEMPLATE.format(
        title=html.escape(listing.get("title") or "Без назви"),
        district=html.escape(str(location)),
        price=html.escape(_format_price(listing)),
        meta=meta_html,
        description=html.escape(listing.get("description") or ""),
        url=html.escape(listing.get("url") or "#"),
    )


def render(data: dict[str, Any]) -> str:
    query = data.get("query") or {}
    listings = data.get("listings") or []
    street = query.get("street")
    city = query.get("city", "Київ")
    generated_at = query.get("generated_at", "")

    title = query.get("title") or (f"Оренда на {street}" if street else "OLX")
    subtitle = query.get("subtitle") or (
        f"Довгострокова оренда квартир, вул. {street}, {city}" if street else query.get("category", "")
    )
    eyebrow = query.get("eyebrow") or ("OLX · довгострокова оренда" if street else "OLX · оголошення")
    icon = ICON_GATE if street else ICON_CHIP

    cards_html = "\n    ".join(_render_card(item) for item in listings) if listings else EMPTY_TEMPLATE
    notice_html = ""
    if data.get("source_note"):
        notice_html = f'<div class="notice"><strong>Про дані.</strong> {html.escape(data["source_note"])}</div>'

    return PAGE_TEMPLATE.format(
        title=html.escape(title),
        subtitle=html.escape(subtitle),
        eyebrow=html.escape(eyebrow),
        icon=icon,
        count=len(listings),
        generated_at=html.escape(generated_at) if generated_at else "&mdash;",
        notice=notice_html,
        cards=cards_html,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to listings JSON (from olx_fetch.py or the sample data).")
    parser.add_argument("output", type=Path, nargs="?", default=Path("report.html"), help="Output HTML file.")
    args = parser.parse_args()

    data = _load(args.input)
    args.output.write_text(render(data), encoding="utf-8")
    print(f"Wrote {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
