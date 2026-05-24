"""Unit testovi za verdict cache + sampler."""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.framework import cache, sampler
from evals.framework.types import EvalEntry, EvalVerdict

pytestmark = pytest.mark.unit


# --------------------------- cache.compute_hash ---------------------------


def _entry(eid: str = "e1", query: str = "q", expect_tool: str = "x") -> EvalEntry:
    return {
        "id": eid,
        "query": query,
        "history": [],
        "expect": {"tool": expect_tool},
        "tags": [],
    }


def test_hash_deterministic_same_input() -> None:
    h1 = cache.compute_hash(_entry(), "prompt", "tools")
    h2 = cache.compute_hash(_entry(), "prompt", "tools")
    assert h1 == h2


def test_hash_changes_on_prompt_change() -> None:
    h1 = cache.compute_hash(_entry(), "prompt-v1", "tools")
    h2 = cache.compute_hash(_entry(), "prompt-v2", "tools")
    assert h1 != h2


def test_hash_changes_on_tools_change() -> None:
    h1 = cache.compute_hash(_entry(), "prompt", "tools-v1")
    h2 = cache.compute_hash(_entry(), "prompt", "tools-v2")
    assert h1 != h2


def test_hash_changes_on_entry_query_change() -> None:
    h1 = cache.compute_hash(_entry(query="abc"), "prompt", "tools")
    h2 = cache.compute_hash(_entry(query="xyz"), "prompt", "tools")
    assert h1 != h2


def test_hash_ignores_tags_field() -> None:
    """Tags su metapodatak za izvještaj, ne utiču na verdict — hash isti."""
    e1: EvalEntry = {**_entry(), "tags": ["auto-gen"]}
    e2: EvalEntry = {**_entry(), "tags": ["manual"]}
    assert cache.compute_hash(e1, "p", "t") == cache.compute_hash(e2, "p", "t")


# --------------------------- cache.get / put ---------------------------


def _verdict(eid: str = "e1", overall: str = "PASS") -> EvalVerdict:
    return {
        "entry_id": eid,
        "routing": "PASS",
        "result": "NA",
        "overall": overall,  # type: ignore[typeddict-item]
        "actual_tool_calls": [],
        "reply": "ok",
        "iterations": 1,
        "error": None,
        "elapsed_ms": 100,
    }


def test_cache_miss_returns_none(tmp_path: Path) -> None:
    assert cache.cache_get(tmp_path, "nonexistent") is None


def test_cache_roundtrip_pass(tmp_path: Path) -> None:
    cache.cache_put(tmp_path, "abc", _verdict(overall="PASS"))
    got = cache.cache_get(tmp_path, "abc")
    assert got is not None
    assert got["overall"] == "PASS"
    assert got["entry_id"] == "e1"


def test_cache_roundtrip_fail(tmp_path: Path) -> None:
    cache.cache_put(tmp_path, "fff", _verdict(overall="FAIL"))
    got = cache.cache_get(tmp_path, "fff")
    assert got is not None
    assert got["overall"] == "FAIL"


def test_cache_skips_na_verdict(tmp_path: Path) -> None:
    """NA verdikte (entry ne testira ništa) ne kešira se."""
    cache.cache_put(tmp_path, "na", _verdict(overall="NA"))
    assert cache.cache_get(tmp_path, "na") is None


def test_cache_stats_empty(tmp_path: Path) -> None:
    stats = cache.cache_stats(tmp_path / "nonexistent")
    assert stats == {"total": 0, "pass": 0, "fail": 0, "warn": 0}


def test_cache_stats_counts(tmp_path: Path) -> None:
    cache.cache_put(tmp_path, "a", _verdict(overall="PASS"))
    cache.cache_put(tmp_path, "b", _verdict(overall="PASS"))
    cache.cache_put(tmp_path, "c", _verdict(overall="FAIL"))
    stats = cache.cache_stats(tmp_path)
    assert stats["total"] == 3
    assert stats["pass"] == 2
    assert stats["fail"] == 1


# --------------------------- sampler ---------------------------


def _tagged_entry(eid: str, tags: list[str]) -> EvalEntry:
    return {
        "id": eid,
        "query": f"q{eid}",
        "history": [],
        "expect": {},
        "tags": tags,
    }


def test_sampler_returns_all_when_below_target() -> None:
    entries = [_tagged_entry(f"e{i}", ["auto-gen", "leaf"]) for i in range(5)]
    result = sampler.stratified_sample(entries, target_size=30)
    assert len(result) == 5


def test_sampler_deterministic_same_seed() -> None:
    entries = [_tagged_entry(f"e{i}", ["auto-gen", "leaf"]) for i in range(50)]
    a = sampler.stratified_sample(entries, target_size=20, seed=42)
    b = sampler.stratified_sample(entries, target_size=20, seed=42)
    assert [e["id"] for e in a] == [e["id"] for e in b]


def test_sampler_different_seed_different_sample() -> None:
    entries = [_tagged_entry(f"e{i}", ["auto-gen", "leaf"]) for i in range(50)]
    a = sampler.stratified_sample(entries, target_size=20, seed=42)
    b = sampler.stratified_sample(entries, target_size=20, seed=123)
    assert [e["id"] for e in a] != [e["id"] for e in b]


def test_sampler_always_includes_manual() -> None:
    """Manual/negative entry-ji uvijek prolaze nezavisno od target_size."""
    manual = [_tagged_entry(f"m{i}", ["manual", "negative"]) for i in range(5)]
    auto = [_tagged_entry(f"a{i}", ["auto-gen", "leaf"]) for i in range(50)]
    result = sampler.stratified_sample(manual + auto, target_size=30)
    manual_ids_in_result = [e["id"] for e in result if e["id"].startswith("m")]
    assert len(manual_ids_in_result) == 5


def test_sampler_balances_parent_leaf() -> None:
    """Bez manual-a, parent i leaf su 50/50 (do raspoloživosti)."""
    parent = [_tagged_entry(f"p{i}", ["auto-gen", "parent"]) for i in range(50)]
    leaf = [_tagged_entry(f"l{i}", ["auto-gen", "leaf"]) for i in range(50)]
    result = sampler.stratified_sample(parent + leaf, target_size=30, seed=42)
    parent_count = sum(1 for e in result if e["id"].startswith("p"))
    leaf_count = sum(1 for e in result if e["id"].startswith("l"))
    # 50/50 split, allow ±1 toleranciju
    assert abs(parent_count - leaf_count) <= 1
