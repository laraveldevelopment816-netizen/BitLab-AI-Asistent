"""
Provjera integriteta `evals/sets/categories_cold.json` i
`evals/sets/products_cold.json` šeme:

- id 4-cifren regex, unique po fajlu.
- XOR polarity: tačno jedan od `expect-positive` / `expect-negative`.
- Pozitivni: non-empty `expect.category_id`.
- Negativni: `expect.tool is None` + `expect.failure_reason` postoji.
- `id` je prvi ključ u JSON objektu (vidljivost u editoru).

Plus sanity provjera za 9 ID-eva NULL routing klastera identifikovanih
u prethodnom run-u — fiksira ih da naredne iteracije ne preimenuju
slučajno.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATEGORIES_PATH = PROJECT_ROOT / "evals" / "sets" / "categories_cold.json"
PRODUCTS_PATH = PROJECT_ROOT / "evals" / "sets" / "products_cold.json"

ID_REGEX = re.compile(r"^\d{4}$")


def _load_json_preserve_order(path: Path) -> list[dict]:
    """JSON load — Python 3.7+ čuva insertion order u dict-u, pa je
    `list(entry.keys())[0]` pouzdano za provjeru "id je prvi ključ"."""
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def categories() -> list[dict]:
    return _load_json_preserve_order(CATEGORIES_PATH)


@pytest.fixture(scope="module")
def products() -> list[dict]:
    return _load_json_preserve_order(PRODUCTS_PATH)


# ── id format + uniqueness ───────────────────────────────────────


@pytest.mark.parametrize("set_name", ["categories", "products"])
def test_every_entry_has_id_field(set_name, categories, products):
    entries = categories if set_name == "categories" else products
    missing = [i for i, e in enumerate(entries) if "id" not in e]
    assert not missing, f"{set_name}: entries bez `id` na indeksima {missing}"


@pytest.mark.parametrize("set_name", ["categories", "products"])
def test_id_matches_4digit_regex(set_name, categories, products):
    entries = categories if set_name == "categories" else products
    bad = [e["id"] for e in entries if not ID_REGEX.match(str(e.get("id", "")))]
    assert not bad, f"{set_name}: ID-evi koji ne match-uju ^\\d{{4}}$: {bad}"


@pytest.mark.parametrize("set_name", ["categories", "products"])
def test_ids_are_unique(set_name, categories, products):
    entries = categories if set_name == "categories" else products
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), (
        f"{set_name}: duplicate ID-evi: "
        f"{[i for i in set(ids) if ids.count(i) > 1]}"
    )


@pytest.mark.parametrize("set_name", ["categories", "products"])
def test_id_is_first_key(set_name, categories, products):
    """id mora biti prvi ključ — vidljivost u JSON editoru, copy-paste
    iz fajla je dosljedan."""
    entries = categories if set_name == "categories" else products
    bad = [
        (e.get("id"), list(e.keys())[0])
        for e in entries
        if list(e.keys())[0] != "id"
    ]
    assert not bad, f"{set_name}: entries gdje id nije prvi ključ: {bad[:5]}"


# ── polarity tag XOR ─────────────────────────────────────────────


@pytest.mark.parametrize("set_name", ["categories", "products"])
def test_polarity_tag_xor(set_name, categories, products):
    """Svaki entry mora imati TAČNO jedan od expect-positive /
    expect-negative."""
    entries = categories if set_name == "categories" else products
    violations = []
    for e in entries:
        tags = e.get("tags") or []
        has_pos = "expect-positive" in tags
        has_neg = "expect-negative" in tags
        if has_pos == has_neg:  # oba True ili oba False
            violations.append((e["id"], tags))
    assert not violations, (
        f"{set_name}: entries bez XOR polarity ({len(violations)}): {violations[:5]}"
    )


# ── pozitivni: cat_id non-empty ──────────────────────────────────


@pytest.mark.parametrize("set_name", ["categories", "products"])
def test_positive_entries_have_category_id(set_name, categories, products):
    entries = categories if set_name == "categories" else products
    missing = []
    for e in entries:
        if "expect-positive" not in (e.get("tags") or []):
            continue
        expect = e.get("expect") or {}
        if not expect.get("category_id"):
            missing.append((e["id"], e.get("query")))
    assert not missing, (
        f"{set_name}: pozitivni entries bez expect.category_id: {missing[:5]}"
    )


# ── negativni: tool=None + failure_reason ────────────────────────


@pytest.mark.parametrize("set_name", ["categories", "products"])
def test_negative_entries_have_no_tool_and_have_reason(set_name, categories, products):
    """Negativni entry: expect.tool == None AND expect.failure_reason
    postoji (neprazan)."""
    entries = categories if set_name == "categories" else products
    violations = []
    for e in entries:
        if "expect-negative" not in (e.get("tags") or []):
            continue
        expect = e.get("expect") or {}
        tool = expect.get("tool", "MISSING")
        reason = expect.get("failure_reason")
        if tool is not None or not reason:
            violations.append((e["id"], e.get("query"), tool, reason))
    assert not violations, (
        f"{set_name}: negativni entries sa invalid expect: {violations[:5]}"
    )


# ── NULL routing klaster sanity (9 ID-eva iz prethodne iteracije) ─


NULL_ROUTING_CLUSTER = {
    "0007": ("Produženje garancije", "101"),
    "0014": ("HDD storage", "114"),
    "0016": ("Optika interna", "116"),
    "0017": ("Graficke kartice", "117"),
    "0018": ("Kućišta", "118"),
    "0028": ("Skeneri", "131"),
    "0038": ("Projektori", "149"),
    "0041": ("Fiksna telefonija", "154"),
    "0050": ("Rezervni dijelovi elektronika", "167"),
}


def test_null_routing_cluster_ids_match_expected(categories):
    """Sanity provjera: 9 ID-eva za NULL routing klaster iz prethodne
    iteracije su pravilno mapirani u categories_cold.json. Bilo koja
    promjena u (id, query, cat_id) pucanjem ovog testa daje signal da
    je drift iz baseline-a."""
    by_id = {e["id"]: e for e in categories}
    for cid, (expected_query, expected_cat) in NULL_ROUTING_CLUSTER.items():
        entry = by_id.get(cid)
        assert entry is not None, f"ID {cid} nedostaje u categories_cold.json"
        assert entry["query"] == expected_query, (
            f"ID {cid}: query='{entry['query']}', očekivano '{expected_query}'"
        )
        actual_cat = (entry.get("expect") or {}).get("category_id")
        assert actual_cat == expected_cat, (
            f"ID {cid}: expect.category_id='{actual_cat}', očekivano '{expected_cat}'"
        )


# ── opšte sanity numbers ─────────────────────────────────────────


def test_categories_set_size_sane(categories):
    """245 entry-ja je trenutna verzija (235 auto-gen + 10 manual neg).
    Tolerancija ±25 da naturalno raste sa taxonomy promjenama, ali ako
    pređe granicu — namjerna izmjena, mijenja se i ovaj test."""
    n = len(categories)
    assert 220 <= n <= 270, f"categories: {n} entry-ja je van očekivanog opsega"


def test_products_set_has_at_least_15(products):
    """Products je ručni, manji set — minimum sanity check."""
    assert len(products) >= 15
