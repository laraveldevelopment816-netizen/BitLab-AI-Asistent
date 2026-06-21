"""Verdict cache — disk-backed lookup po (system_prompt + tools + entry) hash-u.

Cilj: drugi pokušaj istog entry-ja sa istim promptom i tools-ima ne pravi PWR
poziv. Cache hit vraća stored verdict, miss pušta runner da pozove backend.

Hash invariant:
- Promijeniš SYSTEM_PROMPT_V1 → svi hash-evi se mijenjaju → cache se prirodno
  invalidira (lookup miss-uje, runner zove backend).
- Promijeniš tool definiciju (npr. dodaš `brand` arg) → ditto.
- Promijeniš jedan entry tekst → invalidira samo taj.

Disk store: `evals/cache/<hash>.json`. Po hash-u, ne po entry_id-ju, jer isti
entry_id sa drugim promptom mora biti drugi cache zapis.

Memorija anthropic_budget: cache čuva i FAIL verdicte (ne samo PASS) da
ponovni pokušaj fail-a ne košta sesiju kad je uzrok determinističan
(prompt/tool problem, ne LLM nondeterminism).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .types import EvalEntry, EvalVerdict


def compute_hash(entry: EvalEntry, system_prompt: str, tools_signature: str) -> str:
    """SHA-256 hash inputa koji determinišu verdict.

    tools_signature = JSON string ALL_TOOLS_ANTHROPIC (caller dohvata
    iz app.tools jer cache ne smije zavisiti od app/ paketa direktno —
    osim apstraktnog stringa potpisa).
    """
    payload = {
        "entry": _normalize_entry(entry),
        "system_prompt": system_prompt,
        "tools": tools_signature,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_entry(entry: EvalEntry) -> dict[str, Any]:
    """Strogi subset: samo polja koja utiču na rezultat (id + query + history + expect)."""
    return {
        "id": entry["id"],
        "query": entry["query"],
        "history": entry.get("history", []),
        "expect": entry.get("expect", {}),
    }


def cache_get(cache_dir: Path, hash_key: str) -> EvalVerdict | None:
    """Vrati cached verdict ili None ako miss."""
    cache_file = cache_dir / f"{hash_key}.json"
    if not cache_file.exists():
        return None
    try:
        with cache_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def cache_put(cache_dir: Path, hash_key: str, verdict: EvalVerdict) -> None:
    """Snimi verdict u cache. Tihog skipuje ako nije FAIL/PASS/WARN
    (NA verdikte ne keširamo — testiraju ništa, nije win)."""
    if verdict["overall"] == "NA":
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{hash_key}.json"
    enriched = dict(verdict)
    enriched["_cache_hash"] = hash_key
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)


def cache_stats(cache_dir: Path) -> dict[str, int]:
    """Brzi pregled stanja cache-a (broj zapisa po verdict-u)."""
    if not cache_dir.exists():
        return {"total": 0, "pass": 0, "fail": 0, "warn": 0}
    stats = {"total": 0, "pass": 0, "fail": 0, "warn": 0}
    for f in cache_dir.glob("*.json"):
        try:
            with f.open("r", encoding="utf-8") as fh:
                v = json.load(fh)
            stats["total"] += 1
            overall = v.get("overall", "").lower()
            if overall in stats:
                stats[overall] += 1
        except (json.JSONDecodeError, OSError):
            continue
    return stats
