"""
Single source of truth za brendove.

Učitava `data/brend.json` (phpMyAdmin export) jednom pri import-u i
izlaže listu brendova + derivacije koje tools.py i rag.py koriste.

Stara stanja (zamijenjena):
- `_load_brands()` u `app/tools.py:97-118` (sortiralo po priority,
  filtriralo "ostalo", default priority=999).
- `_load_brands()` u `app/rag.py:96-115` (NIJE filtriralo "ostalo",
  default priority=None).

Unifikacija: BRANDS uvijek isključuje "ostalo" (i u rag-u i u tools-u
"ostalo" se ionako preskakao u downstream kodu — vidi rag.py:255-256).
Priority je `int | None` (zadržava semantiku da brend bez priority-ja
nema "rank"); poseban list `BRANDS_SORTED` za tools.py (priority desc,
None na kraju kao 999).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_BRAND_PATH = _DATA_DIR / "brend.json"


def _load_raw() -> list[dict[str, Any]]:
    if not _BRAND_PATH.exists():
        return []
    raw = json.loads(_BRAND_PATH.read_text(encoding="utf-8"))
    for entry in raw:
        if entry.get("type") == "table" and entry.get("name") == "brend":
            return entry.get("data", [])
    return []


def _parse_brands() -> list[dict[str, Any]]:
    """Vrati [{id, name, priority}] iz raw phpMyAdmin row-ova. Filtrira
    "ostalo" (semantika "nepoznat brend", nije pravi brand match) i prazne
    redove. Priority je int 1-20 ili None."""
    out: list[dict[str, Any]] = []
    for row in _load_raw():
        bid = (row.get("id") or "").strip()
        name = (row.get("name") or "").strip()
        if not bid or not name or name.lower() == "ostalo":
            continue
        pri_raw = row.get("priority")
        priority: int | None
        if pri_raw and pri_raw != "NULL":
            try:
                priority = int(pri_raw)
            except (ValueError, TypeError):
                priority = None
        else:
            priority = None
        out.append({"id": bid, "name": name, "priority": priority})
    return out


BRANDS: list[dict[str, Any]] = _parse_brands()
"""Lista {id, name, priority} — neuređena. priority je int 1-20 ili None.
"ostalo" filtriran."""

BRANDS_SORTED: list[dict[str, Any]] = sorted(
    BRANDS,
    key=lambda b: (b["priority"] if b["priority"] is not None else 999, b["name"]),
)
"""Lista BRANDS sortirana po priority (None → 999 za sortiranje, ide na
kraj). Koristi se u tool description-u — top brendovi prvi."""

BRAND_IDS: list[str] = [b["id"] for b in BRANDS_SORTED]


def render_brands_block() -> str:
    """Renderuj listu brendova za tool description (sortirano)."""
    return "\n".join(f"- {b['id']}: {b['name']}" for b in BRANDS_SORTED)


BRANDS_BLOCK: str = render_brands_block()
