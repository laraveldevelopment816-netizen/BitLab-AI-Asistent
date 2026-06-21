"""Stratified sampling za sample-first eval mode.

Cilj: smanjiti broj PWR poziva sa 250 na ~30 stratificiranih + uvijek manual 16
(ako su u istom suite-u kroz tag) = ~46 poziva po Ralph iteraciji (18% troška full).

Stratifikacija po `tags`:
- parent vs leaf (auto-gen): balansirano (15 parent + 15 leaf ako ima dovoljno).
- manual/negative: uvijek SVI uključeni (već su mali set, 16-20 entry-ja).
- edge cases: prioritet preko default-a.

Deterministički: isti seed → isti sample → reproducibilan signal.
"""

from __future__ import annotations

import random
from typing import Any

from .types import EvalEntry


def stratified_sample(
    entries: list[EvalEntry],
    target_size: int = 30,
    seed: int = 42,
) -> list[EvalEntry]:
    """Vrati stratificirani sample iz entries po `tags`.

    Strategija:
    1. Sve manual/negative entry-je UVIJEK uključi (mala grupa, kritičan signal).
    2. Iz auto-gen popuni do target_size sa parent/leaf balansirano (~50/50).
    3. Ako entries < target_size, vrati sve.
    """
    if len(entries) <= target_size:
        return list(entries)

    rng = random.Random(seed)

    # Fix #4: dedup po ID-u — entry sa istovremeno manual + auto-gen + parent
    # tagovima ne smije se duplicirati u rezultatu. Manual ima prednost
    # (uvijek prolazi), auto-gen pool filter-uje ID-eve već u manual-u.
    manual = [e for e in entries if _has_tag(e, "manual") or _has_tag(e, "negative")]
    manual_ids = {e["id"] for e in manual}
    auto_parent = [
        e
        for e in entries
        if _has_tag(e, "auto-gen") and _has_tag(e, "parent") and e["id"] not in manual_ids
    ]
    auto_leaf = [
        e
        for e in entries
        if _has_tag(e, "auto-gen") and _has_tag(e, "leaf") and e["id"] not in manual_ids
    ]

    selected: list[EvalEntry] = list(manual)

    remaining = max(0, target_size - len(selected))
    parent_quota = remaining // 2
    leaf_quota = remaining - parent_quota

    selected.extend(_safe_sample(rng, auto_parent, parent_quota))
    selected.extend(_safe_sample(rng, auto_leaf, leaf_quota))

    # Ako jedna grupa nije imala dovoljno, dopuni iz preostalih neselektovanih.
    if len(selected) < target_size:
        already = {e["id"] for e in selected}
        rest = [e for e in entries if e["id"] not in already]
        rng.shuffle(rest)
        selected.extend(rest[: target_size - len(selected)])

    return selected


def _has_tag(entry: EvalEntry, tag: str) -> bool:
    tags: list[Any] = entry.get("tags", []) or []
    return tag in tags


def _safe_sample(rng: random.Random, items: list[EvalEntry], k: int) -> list[EvalEntry]:
    if k <= 0 or not items:
        return []
    if k >= len(items):
        return list(items)
    return rng.sample(items, k)
