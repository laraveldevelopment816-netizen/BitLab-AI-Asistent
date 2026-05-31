"""
Single source of truth za kategorije.

Učitava taxonomy fajl jednom pri import-u i izlaže sve derivacije koje
ostatak koda koristi:
- `CATEGORIES` (aktivni, status=1) — enum + label-i za search_products tool
- `PARENT_CATEGORIES` (parent_id=0 sa ≥2 djece) — breakdown za category_overview
- `CAT_DESCENDANTS` (cid → set descendants) — hard filter parent expansion u rag.py
- `CHILDREN_OF` (cid → direct children list) — eval skripte i tree walking
- `ACTIVE_IDS` / `ALL_IDS` — pomoćni set-ovi za drift dijagnostiku
- `iter_raw_entries()` / `get_raw_entry()` — sirov build-time pristup

Bogatije labele iz starog 50-bucket subset-a se zadržavaju preko
`data/category_label_overrides.json` (ručno održavan fajl). Override fajl
može imati ID-eve koji više ne postoje u taxonomy-ju (npr. legacy bucket
125) — loader ih ignoriše uz warning log.

**SSOT pravilo**: SAMO ovaj modul smije direktno čitati taxonomy fajl
(put-konstanta `_CATEGORIES_NEW_PATH` ispod). Svi ostali konzumenti
(tools.py, rag.py, evals, scripts, tests) idu kroz public API ovog modula.

Refaktor history: ovaj modul je nastao tokom SSOT migracije koja je
ukinula paralelne legacy data fajlove. Plan: `SSOT-categories-refactor-plan.md`.
Razlog migracije: tri paralelna data source-a sa nepoklapajućim ID set-ovima
su uzrokovala 7 OUT routing FAIL-ova u categories eval-u (cat 125 halucinacija).
"""
from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CATEGORIES_NEW_PATH = _DATA_DIR / "categories_new.json"
_LABEL_OVERRIDES_PATH = _DATA_DIR / "category_label_overrides.json"
_PRODUCTS_META_PATH = _DATA_DIR / "products.meta.json"


def _load_raw_categories() -> list[dict[str, Any]]:
    if not _CATEGORIES_NEW_PATH.exists():
        return []
    return json.loads(_CATEGORIES_NEW_PATH.read_text(encoding="utf-8"))


def _load_label_overrides() -> dict[str, str]:
    """Ručne labele iz starog `categories.json`-a (npr. "Printeri
    (raznovrsni — Epson, HP, Canon)") — bogatije od golog `name` polja
    u taxonomy-ju. Override fajl može imati ID-eve koji više ne postoje
    u taxonomy-ju; ti se ignorišu uz warning."""
    if not _LABEL_OVERRIDES_PATH.exists():
        return {}
    try:
        return json.loads(_LABEL_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Override fajl ne može biti parsiran: %s", e)
        return {}


def _load_product_counts() -> dict[str, int]:
    """Iz `products.meta.json` izračunaj broj proizvoda po cat_id-u.
    Koristi se za filtriranje enum-a u tool description-u (kategorije
    sa 0 proizvoda nemaju smisla u enum-u) i kao polje u CATEGORIES."""
    if not _PRODUCTS_META_PATH.exists():
        return {}
    meta = json.loads(_PRODUCTS_META_PATH.read_text(encoding="utf-8"))
    products = meta.get("products", {})
    counts: Counter[str] = Counter()
    for p in products.values():
        cid = (p.get("categories_id") or "").strip()
        if cid:
            counts[cid] += 1
    return dict(counts)


def _pick_label(c: dict[str, Any], overrides: dict[str, str]) -> str:
    """Override → h1_title → name. h1_title je obično bogatiji ("Računari
    – Desktop, Laptop i All-in-One") nego goli name ("Računari")."""
    cid = str(c.get("id"))
    if cid in overrides:
        return overrides[cid]
    h1 = (c.get("h1_title") or "").strip()
    if h1:
        return h1
    return (c.get("name") or "").strip()


def _build_descendants(by_id: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    """cat_id → {cat_id i svi descendant-i}. Koristi se za parent expansion
    u hard filteru pretrage (rag.py). Inaktivni cat-ovi (status!=1) se
    preskaču — replicira ponašanje starog `_load_cat_descendants` koji je
    radio nad CSV-om sa `status=1` filterom."""
    children: dict[str, list[str]] = defaultdict(list)
    active_ids: set[str] = set()
    for cid, c in by_id.items():
        if c.get("status") != 1:
            continue
        active_ids.add(cid)
        pid_raw = c.get("parent_id")
        if pid_raw and pid_raw != 0:
            children[str(pid_raw)].append(cid)

    def _walk(cat: str) -> set[str]:
        result = {cat}
        for child in children.get(cat, []):
            result |= _walk(child)
        return result

    return {cid: _walk(cid) for cid in active_ids}


# ── Init at import-time ──────────────────────────────────────────

_raw = _load_raw_categories()
_overrides = _load_label_overrides()
_counts = _load_product_counts()

# {cid_str: full taxonomy dict} — sve kategorije iz fajla, bez filter-a
_BY_ID: dict[str, dict[str, Any]] = {str(c["id"]): c for c in _raw}

ALL_IDS: set[str] = set(_BY_ID.keys())
ACTIVE_IDS: set[str] = {cid for cid, c in _BY_ID.items() if c.get("status") == 1}

# Warning ako override referencira nepostojeći ID — drift dijagnostika
_orphan_overrides = set(_overrides) - ALL_IDS
if _orphan_overrides:
    logger.warning(
        "category_label_overrides.json sadrži ID-eve koji ne postoje u "
        "taxonomy-ju (ignorisani): %s",
        sorted(_orphan_overrides),
    )

# Public dict: cid → kompaktan view koji ostatak app-a koristi
CATEGORIES: dict[str, dict[str, Any]] = {
    cid: {
        "label": _pick_label(c, _overrides),
        "urlhash": (c.get("urlhash") or "").strip(),
        "parent_id": str(c.get("parent_id") or 0),
        "status": c.get("status"),
        "name": (c.get("name") or "").strip(),
        "count": _counts.get(cid, 0),
    }
    for cid, c in _BY_ID.items()
    if c.get("status") == 1  # search-relevantno = samo aktivno
}

CAT_DESCENDANTS: dict[str, set[str]] = _build_descendants(_BY_ID)


def _build_direct_children() -> dict[str, list[str]]:
    """parent_id → lista direktnih djece (samo prvi nivo).

    Sloj nad CAT_DESCENDANTS-om: ulaze samo aktivne djece (status=1) ČIJI
    je parent takođe aktivan. Tako se izbjegava drift gdje child ima
    inactive parent-a — taj parent nikad nije reference target u runtime
    AI tools (nije u CATEGORIES), pa ne smije ni u CHILDREN_OF.

    Eval skripte koriste ovo umjesto da samostalno čitaju taxonomy fajl."""
    out: dict[str, list[str]] = defaultdict(list)
    for cid, c in _BY_ID.items():
        if c.get("status") != 1:
            continue
        pid_raw = c.get("parent_id")
        if not pid_raw or pid_raw == 0:
            continue
        pid_str = str(pid_raw)
        # Parent mora biti aktivan da bi se mapiranje uopšte pamtilo.
        parent = _BY_ID.get(pid_str)
        if not parent or parent.get("status") != 1:
            continue
        out[pid_str].append(cid)
    return dict(out)


CHILDREN_OF: dict[str, list[str]] = _build_direct_children()
"""Direct-child mapa: parent_cid → [child_cid, ...]. Ne sadrži unuke
(za to vidi CAT_DESCENDANTS)."""


def _build_parent_categories() -> dict[str, dict[str, Any]]:
    """parent_id=0 cat-ovi sa ≥2 aktivne djece — za `category_overview`
    tool. Replicira `_load_parent_categories` iz `app/tools.py`."""
    children_of: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for c in _raw:
        if c.get("status") != 1:
            continue
        p = c.get("parent_id")
        if p and p != 0:
            children_of[p].append(c)
    out: dict[str, dict[str, Any]] = {}
    for c in _raw:
        if c.get("status") != 1:
            continue
        if c.get("parent_id") != 0:
            continue
        cid_int = c["id"]
        kids = children_of.get(cid_int, [])
        if len(kids) < 2:
            continue
        kids_sorted = sorted(
            kids, key=lambda k: (k.get("sort_id") or 999, k.get("name") or "")
        )
        out[str(cid_int)] = {
            "label": _pick_label(c, _overrides),
            "urlhash": (c.get("urlhash") or "").strip(),
            "children": [
                {
                    "cat_id": str(k["id"]),
                    "label": _pick_label(k, _overrides),
                    "urlhash": (k.get("urlhash") or "").strip(),
                }
                for k in kids_sorted
            ],
        }
    return out


PARENT_CATEGORIES: dict[str, dict[str, Any]] = _build_parent_categories()


def get_active_ids_with_products(min_products: int = 1) -> list[str]:
    """Vrati aktivne cat_id-ove koji imaju ≥ min_products proizvoda.
    Koristi se za enum filtriranje u tool description-u: kategorije sa
    0 proizvoda zbune Claude-a i nepotrebno povećavaju token cost.

    Sortirano: po parent_id (grupisano), pa po count (više prvo), pa po
    label (alfabetski tie-break)."""
    eligible = [
        cid
        for cid, info in CATEGORIES.items()
        if info["count"] >= min_products
    ]
    eligible.sort(
        key=lambda cid: (
            int(CATEGORIES[cid]["parent_id"] or 0),
            -CATEGORIES[cid]["count"],
            CATEGORIES[cid]["label"],
        )
    )
    return eligible


def render_categories_block(ids: list[str] | None = None) -> str:
    """Renderuj `_CATEGORIES_BLOCK` koji ide u tool description.
    Ako `ids` nije zadano, uzima sve aktivne sa ≥1 proizvod."""
    if ids is None:
        ids = get_active_ids_with_products(min_products=1)
    return "\n".join(f"- {cid}: {CATEGORIES[cid]['label']}" for cid in ids)


def render_parents_block() -> str:
    """Renderuj `_PARENTS_BLOCK` koji ide u `category_overview` description."""
    return "\n".join(
        f"- {pid}: {p['label']} (djeca: {', '.join(c['label'] for c in p['children'])})"
        for pid, p in PARENT_CATEGORIES.items()
    )


# ── Build-time API ───────────────────────────────────────────────
# Sledeće funkcije izlažu sirove taxonomy entry-je i koriste se SAMO u
# build-time skriptama (scripts/build_category_terms.py, scripts/gen_categories_eval.py)
# i parity testovima. Runtime kod (tools.py, rag.py, agent.py) ne smije
# ih koristiti — radi sa visokim API-jem (CATEGORIES, PARENT_CATEGORIES,
# CAT_DESCENDANTS, CHILDREN_OF).


def iter_raw_entries(active_only: bool = True):
    """Iteriraj kroz sirove taxonomy entry-je (sva polja iz fajla:
    name, h1_title, meta_keywords, sort_id, urlhash, status, parent_id, ...).

    Args:
        active_only: kad je True (default), preskače status≠1 entry-je.
    Yields:
        (cid_str, raw_dict) parove."""
    for cid, c in _BY_ID.items():
        if active_only and c.get("status") != 1:
            continue
        yield cid, c


def get_raw_entry(cid: str) -> dict[str, Any] | None:
    """Vrati sirov entry za cat_id (sva polja iz taxonomy fajla) ili None
    ako cat ne postoji. Build-time only."""
    return _BY_ID.get(cid)
