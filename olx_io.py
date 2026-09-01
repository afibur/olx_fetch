"""Save fetched OLX listings in the JSON/CSV shape render_report.py reads."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from olx_api import Listing


def save_listings(
    listings: list[Listing],
    path: Path,
    query: dict[str, Any] | None = None,
    source_note: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(item) for item in listings]

    if path.suffix == ".csv":
        with path.open("w", newline="", encoding="utf-8") as f:
            fieldnames = list(rows[0].keys()) if rows else []
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({**row, "tags": " | ".join(row.get("tags") or [])})
        return

    document = {"query": query or {}, "source_note": source_note, "listings": rows}
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
