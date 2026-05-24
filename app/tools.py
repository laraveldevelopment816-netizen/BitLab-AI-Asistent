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


def _category_block() -> str:
    """`- id: ime` lista — daje modelu mapping ime→ID da popuni `category_id`.

    Bez ovoga model nema kako da zna da "Računari" → 17. Tool description je
    primarno mjesto za ovu info (ne sistem prompt) jer ostaje skopčano sa
    tool-om i ne curi u kontekst drugih scenarija.
    """
    return "\n".join(
        f"- {int(c['id'])}: {str(c['name']).strip()}"
        for c in sorted(_CATEGORIES, key=lambda c: int(c["id"]))
    )


CATEGORY_OVERVIEW_TOOL: dict[str, Any] = {
    "name": "category_overview",
    "description": (
        "Prikaži pregled potkategorija unutar parent kategorije. "
        "Pozovi kad korisnik traži pregled kategorije koja ima potkategorije "
        "(npr. 'Računari', 'Printeri i skeneri').\n\n"
        "VALIDNI category_id-ovi (mapping ime → ID):\n"
        f"{_category_block()}"
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

ALL_TOOLS_ANTHROPIC: list[dict[str, Any]] = [CATEGORY_OVERVIEW_TOOL]


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


def dispatch(name: str, args: dict[str, Any]) -> str:
    """Tool name → handler. Vraća string sadržaj za tool_result poruku.

    Nepoznat tool → JSON error payload (model dobija error i može fallback-ovati
    na tekst odgovor, umjesto da runner crash-uje).
    """
    if name == "category_overview":
        return _handle_category_overview(args)
    return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
