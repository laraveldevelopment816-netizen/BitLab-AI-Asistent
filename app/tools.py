"""Tool definicije + dispatch — jedan SSOT za OBA LLM backend-a.

Pravila (spec specs/categories.md §3.1 + ralph/AGENTS.md):
- Tool je definisan u Anthropic shape (sa `input_schema`).
- OpenAI shape (`{type:"function", function:{name, description, parameters}}`)
  se DERIVIRA iz Anthropic shape-a (ne dupliciraj rukom — drift rizik).
- `dispatch(name, args)` je shape-agnostic: uzima naziv toola i dict argumenata,
  vraća string (JSON ili plain text) koji se vraća modelu kao tool_result.

Acceptance Fase 1 task 1: handler stub `category_overview` vraća listu djece
iz `data/categories_new.json`. Pravi RAG dolazi tek u Fazi 2 sa
`search_products`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CATEGORIES_PATH = _DATA_DIR / "categories_new.json"


def _load_categories() -> list[dict[str, Any]]:
    if not _CATEGORIES_PATH.exists():
        return []
    return json.loads(_CATEGORIES_PATH.read_text(encoding="utf-8"))


_CATEGORIES: list[dict[str, Any]] = _load_categories()
_CHILDREN_BY_PARENT: dict[int, list[dict[str, Any]]] = defaultdict(list)
for _cat in _CATEGORIES:
    _CHILDREN_BY_PARENT[int(_cat["parent_id"])].append(_cat)

# Parent = kategorija čiji se `id` pojavljuje kao `parent_id` neke druge.
# `parent_id=0` je sentinel za root, pa ga skipujemo. Leaf = sve ostalo.
_PARENT_IDS: set[int] = {int(c["parent_id"]) for c in _CATEGORIES if int(c["parent_id"]) != 0}


def _parent_block() -> str:
    """`- id: ime` lista samo parent kategorija (id koji je nečiji parent_id).

    Koristi se u `category_overview` description-u da modelu pokaže SAMO
    validne parent ID-ove — sprječava da pozove `category_overview` za leaf
    (gdje rezultat bi bio prazan `children: []`).
    """
    return "\n".join(
        f"- {int(c['id'])}: {str(c['name']).strip()}"
        for c in sorted(_CATEGORIES, key=lambda c: int(c["id"]))
        if int(c["id"]) in _PARENT_IDS
    )


def _leaf_block() -> str:
    """`- id: ime` lista samo leaf kategorija (id koji nije ničiji parent_id).

    Koristi se u `search_products` description-u da modelu pokaže SAMO leaf
    ID-ove — proizvodi žive samo na leaf nivou.
    """
    return "\n".join(
        f"- {int(c['id'])}: {str(c['name']).strip()}"
        for c in sorted(_CATEGORIES, key=lambda c: int(c["id"]))
        if int(c["id"]) not in _PARENT_IDS
    )


CATEGORY_OVERVIEW_TOOL: dict[str, Any] = {
    "name": "category_overview",
    "description": (
        "Prikaži pregled potkategorija unutar PARENT kategorije. "
        "Pozovi SAMO kad upit odgovara parent kategoriji iz liste ispod "
        "(npr. 'Računari', 'Printeri i skeneri') — parent ima potkategorije. "
        "Za listing proizvoda u LEAF kategoriji koristi search_products.\n\n"
        "VALIDNI PARENT category_id-ovi (mapping ime → ID):\n"
        f"{_parent_block()}"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category_id": {
                "type": "integer",
                "description": "ID parent kategorije iz mapping liste iznad.",
            },
        },
        "required": ["category_id"],
    },
}

SEARCH_PRODUCTS_TOOL: dict[str, Any] = {
    "name": "search_products",
    "description": (
        "Pretraga proizvoda u LEAF kategoriji (kategorija bez potkategorija). "
        "Pozovi kad upit odgovara leaf kategoriji iz liste ispod "
        "(npr. 'Notebook', 'Tablet', 'Desktop Brand Name') ili kad korisnik "
        "traži konkretne proizvode/brendove. Za parent kategoriju (sa "
        "potkategorijama) koristi category_overview umjesto toga.\n\n"
        "VALIDNI LEAF category_id-ovi (mapping ime → ID):\n"
        f"{_leaf_block()}"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Slobodni tekst pretrage (npr. ime proizvoda ili kategorije).",
            },
            "category_id": {
                "type": "integer",
                "description": "Suzi pretragu na leaf kategoriju iz mapping liste iznad.",
            },
            "brand": {
                "type": "string",
                "description": "Filter brenda (npr. 'Samsung', 'HP').",
            },
            "max_price_km": {
                "type": "number",
                "description": "Maksimalna cijena u KM.",
            },
            "min_price_km": {
                "type": "number",
                "description": "Minimalna cijena u KM.",
            },
        },
    },
}

RESPOND_TO_USER_TOOL: dict[str, Any] = {
    "name": "respond_to_user",
    "description": (
        "Odgovori korisniku slobodnim tekstom. Koristi kad upit NIJE iz kataloga "
        "(knjige, vrijeme, garancija…), kad je dvosmislen ili izgleda kao typo, ili "
        "za FINALNI odgovor korisniku nakon što su kataloški alati vratili rezultat. "
        "Tvoj tekst ide u `message`. Ne navodi kataloške podatke bez tool rezultata."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Tekst koji se prikazuje korisniku.",
            },
        },
        "required": ["message"],
    },
}

ALL_TOOLS_ANTHROPIC: list[dict[str, Any]] = [
    CATEGORY_OVERVIEW_TOOL,
    SEARCH_PRODUCTS_TOOL,
    RESPOND_TO_USER_TOOL,
]


def _to_openai_shape(tool: dict[str, Any]) -> dict[str, Any]:
    """Anthropic → OpenAI tool shape derivacija (1:1 polje-za-polje).

    Anthropic: {name, description, input_schema}
    OpenAI:    {type:"function", function:{name, description, parameters}}
    """
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


ALL_TOOLS_OPENAI: list[dict[str, Any]] = [_to_openai_shape(t) for t in ALL_TOOLS_ANTHROPIC]


def _handle_category_overview(args: dict[str, Any]) -> str:
    """Stub handler: lista djece parent kategorije iz `data/categories_new.json`.

    Vraća JSON string `{"category_id": N, "children": [{"id":..,"name":..}, ...]}`.
    Bez djece (leaf ili nepostojeći ID) → `children: []`.
    """
    try:
        cid = int(args.get("category_id", 0))
    except (TypeError, ValueError):
        cid = 0
    children = _CHILDREN_BY_PARENT.get(cid, [])
    payload = {
        "category_id": cid,
        "children": [{"id": int(c["id"]), "name": str(c["name"]).strip()} for c in children],
    }
    return json.dumps(payload, ensure_ascii=False)


def _handle_search_products(args: dict[str, Any]) -> str:
    """Stub handler: prazna lista proizvoda. Pravi RAG dolazi u Fazi 2.

    Vraća JSON string `{"products": [], "category_id"?: N, "query"?: "..."}`.
    Optional polja se uključuju samo ako ih je model proslijedio — eval framework
    poredi `args_subset` pa je dovoljno da `tool_calls` kapsulira args; handler
    rezultat samo treba da bude validan JSON koji model može parsirati.
    """
    payload: dict[str, Any] = {"products": []}
    if "category_id" in args:
        try:
            payload["category_id"] = int(args["category_id"])
        except (TypeError, ValueError):
            pass
    if "query" in args and args["query"] is not None:
        payload["query"] = str(args["query"])
    if "brand" in args and args["brand"] is not None:
        payload["brand"] = str(args["brand"])
    if "min_price_km" in args and args["min_price_km"] is not None:
        try:
            payload["min_price_km"] = float(args["min_price_km"])
        except (TypeError, ValueError):
            pass
    if "max_price_km" in args and args["max_price_km"] is not None:
        try:
            payload["max_price_km"] = float(args["max_price_km"])
        except (TypeError, ValueError):
            pass
    return json.dumps(payload, ensure_ascii=False)


def dispatch(name: str, args: dict[str, Any]) -> str:
    """Tool name → handler. Vraća string sadržaj za tool_result poruku.

    Nepoznat tool → JSON error payload (model dobija error i može fallback-ovati
    na tekst odgovor, umjesto da runner crash-uje).
    """
    if name == "category_overview":
        return _handle_category_overview(args)
    if name == "search_products":
        return _handle_search_products(args)
    return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
