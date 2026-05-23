"""JSONL loader za eval setove.

Jedan entry per line. Linije koje počinju sa `//` ili su prazne se ignorišu
(omogućava komentare unutar fajla).
"""

from __future__ import annotations

import json
from pathlib import Path

from .types import EvalEntry


def load_suite(suite_path: Path) -> list[EvalEntry]:
    """Učita JSONL eval set. Validuje obavezna polja, defaultuje opciona."""
    entries: list[EvalEntry] = []
    with suite_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("//"):
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError as e:
                raise ValueError(f"{suite_path}:{line_no} — JSON parse error: {e}") from e
            _validate_entry(entry, suite_path, line_no)
            entries.append(entry)
    return entries


def _validate_entry(entry: dict, suite_path: Path, line_no: int) -> None:
    for required in ("id", "query", "expect"):
        if required not in entry:
            raise ValueError(f"{suite_path}:{line_no} — entry nedostaje '{required}': {entry}")
    if not isinstance(entry["expect"], dict):
        raise ValueError(f"{suite_path}:{line_no} — 'expect' mora biti dict")
    entry.setdefault("history", [])
    entry.setdefault("tags", [])
