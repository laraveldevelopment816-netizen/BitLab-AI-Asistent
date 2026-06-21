"""
Testovi za `evals/_cli_filters.py` — čista logika koja se može testirati
bez servera.

Pokriva:
- `parse_ids_spec` — sve formate (single, comma, range, mixed, padding,
  whitespace, edge cases).
- `apply_filters` — semantika --query / --ids / --tag i njihove
  kombinacije (AND presjek).
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = PROJECT_ROOT / "evals"
sys.path.insert(0, str(EVALS_DIR))

from _cli_filters import apply_filters, parse_ids_spec  # noqa: E402


# ── parse_ids_spec ───────────────────────────────────────────────


def test_parse_ids_spec_single():
    assert parse_ids_spec("0007") == {"0007"}


def test_parse_ids_spec_comma_list():
    assert parse_ids_spec("0001,0023,0091") == {"0001", "0023", "0091"}


def test_parse_ids_spec_range_inclusive():
    assert parse_ids_spec("0001-0009") == {f"{n:04d}" for n in range(1, 10)}


def test_parse_ids_spec_mixed():
    assert parse_ids_spec("0001-0003,0050") == {"0001", "0002", "0003", "0050"}


def test_parse_ids_spec_padding_normalizes():
    """Numerički ulaz se pad-uje na 4 cifre."""
    assert parse_ids_spec("7") == {"0007"}


def test_parse_ids_spec_whitespace_tolerated():
    assert parse_ids_spec("0001, 0023") == {"0001", "0023"}


def test_parse_ids_spec_empty():
    assert parse_ids_spec("") == set()


def test_parse_ids_spec_range_single_element():
    assert parse_ids_spec("0005-0005") == {"0005"}


def test_parse_ids_spec_reverse_range_returns_empty():
    """Reverse range (`0009-0001`) trenutno daje prazno (Python `range`
    semantika). Test fiksira to ponašanje — ako se mijenja na exception,
    ovaj test treba update."""
    assert parse_ids_spec("0009-0001") == set()


def test_parse_ids_spec_invalid_token_fallback():
    """Token koji nije ni broj ni range trenutno fall-backuje kao literal
    string. Fiksiramo ponašanje — ako se mijenja na exception, update."""
    assert parse_ids_spec("abcd") == {"abcd"}


def test_parse_ids_spec_ignores_empty_chunks():
    """Trailing comma ili dupli comma ne pravi prazne entry-je."""
    assert parse_ids_spec("0001,,0002,") == {"0001", "0002"}


# ── apply_filters ────────────────────────────────────────────────


@pytest.fixture
def sample_queries() -> list[dict]:
    """Minimalan set za apply_filters testove — pokriva polarity,
    auto-gen vs manual, leaf vs parent, te negativan failure_reason tag."""
    return [
        {"id": "0001", "query": "Računari",     "tags": ["auto-gen", "parent", "expect-positive"]},
        {"id": "0002", "query": "Laptop",       "tags": ["auto-gen", "leaf",   "expect-positive"]},
        {"id": "0003", "query": "Mobiteli",     "tags": ["auto-gen", "parent", "expect-positive"]},
        {"id": "0010", "query": "automobili",   "tags": ["manual", "negative", "not_in_catalog", "expect-negative"]},
        {"id": "0011", "query": "knjige",       "tags": ["manual", "negative", "not_in_catalog", "expect-negative"]},
    ]


def _args(**kwargs):
    """Helper: napravi SimpleNamespace sa default None za ids/tag/query."""
    defaults = {"ids": None, "tag": None, "query": None}
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def test_apply_filters_no_flags_unchanged(sample_queries):
    result = apply_filters(sample_queries, _args())
    assert result == sample_queries


def test_apply_filters_query_overrides_all(sample_queries):
    result = apply_filters(sample_queries, _args(query="ad-hoc upit"))
    assert len(result) == 1
    assert result[0]["id"] == "ADHOC"
    assert result[0]["query"] == "ad-hoc upit"
    assert "adhoc" in result[0]["tags"]


def test_apply_filters_query_ignores_other_filters(sample_queries):
    """Kad se --query pošalje, ostali filteri se ignorišu."""
    result = apply_filters(sample_queries, _args(query="x", ids="0001", tag=["expect-positive"]))
    assert len(result) == 1
    assert result[0]["id"] == "ADHOC"


def test_apply_filters_ids_single(sample_queries):
    result = apply_filters(sample_queries, _args(ids="0001"))
    assert [e["id"] for e in result] == ["0001"]


def test_apply_filters_ids_range(sample_queries):
    result = apply_filters(sample_queries, _args(ids="0001-0003"))
    assert {e["id"] for e in result} == {"0001", "0002", "0003"}


def test_apply_filters_tag_positive(sample_queries):
    result = apply_filters(sample_queries, _args(tag=["expect-positive"]))
    assert len(result) == 3
    assert all("expect-positive" in e["tags"] for e in result)


def test_apply_filters_ids_and_tag_intersection(sample_queries):
    """--ids 0001,0002 + --tag expect-positive = oba uslova moraju biti
    ispunjena (AND presjek)."""
    result = apply_filters(sample_queries, _args(ids="0001,0002", tag=["expect-positive"]))
    assert {e["id"] for e in result} == {"0001", "0002"}


def test_apply_filters_ids_and_tag_intersection_disjoint(sample_queries):
    """Ako se --ids i --tag ne preklapaju, rezultat je prazan."""
    result = apply_filters(sample_queries, _args(ids="0001,0002", tag=["expect-negative"]))
    assert result == []


def test_apply_filters_multiple_tags_and(sample_queries):
    """`--tag a --tag b` znači a AND b — entry mora imati oba tag-a."""
    result = apply_filters(sample_queries, _args(tag=["expect-negative", "not_in_catalog"]))
    assert {e["id"] for e in result} == {"0010", "0011"}


def test_apply_filters_multiple_tags_no_overlap(sample_queries):
    """Tag-ovi koji se ne preklapaju → prazno."""
    result = apply_filters(sample_queries, _args(tag=["expect-positive", "expect-negative"]))
    assert result == []


def test_apply_filters_nonexistent_id_empty(sample_queries):
    """--ids 9999 (nepostojeći) → alat odgovornost da hendluje prazno;
    apply_filters sam vraća praznu listu."""
    result = apply_filters(sample_queries, _args(ids="9999"))
    assert result == []
