"""
Regression test: Sesija 8 hotfix.

Production prezentacija je otkrila bug — Haiku je na "Imate li lapatovoe"
(typo za "laptop") tražio pojašnjenje umjesto pretrage, a u sledećem
turu je čak halucinirao "nema dostupnih laptopa" iako catalog ima 50.

Cilj testova: verifikuj da agent (sad Sonnet 4.6) na typo upite:
1. POZOVE search_products u prvoj iteraciji (ne traži pojašnjenje)
2. Sa ispravnim category_id-om
3. NIKAD ne kaže "nema laptopa" kad smo upravo dobili rezultate

Ovi testovi koriste pravi Anthropic API poziv pa su skupi (~$0.02 po
test run-u). Skipni ih u CI ako je potrebno preko `-m "not anthropic_api"`.
"""
from __future__ import annotations

import pytest

from app.agent import run_agent


pytestmark = pytest.mark.anthropic_api


# (typo_query, expected_category_id, expected_phrase_in_query_normalized)
TYPO_CASES = [
    ("Imate li lapatovoe",     "98",  "laptop"),
    ("trazim laptopov",        "98",  "laptop"),
    ("trebamo masku za telfon", "394", "mask"),    # match-uje "maska" ili "mask"
    ("dajte mi tastruru",      "220", "tastat"),
    ("imate li monjitor",      "224", "monit"),
]


@pytest.mark.parametrize("query,expected_cat,expected_query_substr", TYPO_CASES)
def test_typo_triggers_search_with_correct_category(
    query: str, expected_cat: str, expected_query_substr: str,
):
    """Agent na typo upit MORA pozvati search_products u prvoj iteraciji
    sa tačnim category_id-om i normalizovanim query-jem (bez typo-a)."""
    result = run_agent([{"role": "user", "content": query}], "chat")
    trace = result["_trace"]

    # 1. Mora postojati bar jedan tool call u prvoj iteraciji
    first_iter_calls = [tc for tc in trace["tool_calls"] if tc["iteration"] == 1]
    assert first_iter_calls, (
        f"Agent nije pozvao tool u prvoj iteraciji za '{query}' — "
        f"vjerovatno traži pojašnjenje. Reply: {result['reply'][:200]!r}"
    )

    # 2. Prvi tool call mora biti search_products
    first_call = first_iter_calls[0]
    assert first_call["tool_name"] == "search_products", (
        f"Očekivao search_products kao prvi tool, dobio {first_call['tool_name']!r}"
    )

    # 3. Mora imati category_id koji odgovara očekivanoj klasi
    import json as _json
    inp = _json.loads(first_call["input_json"])
    assert inp.get("category_id") == expected_cat, (
        f"Pogrešan category_id za '{query}': "
        f"očekivao {expected_cat}, dobio {inp.get('category_id')!r}"
    )

    # 4. Query parametar treba biti normalizovan (bez typo-a) — provjeri da
    #    sadrži substring koji odgovara namjeri
    query_param = (inp.get("query") or "").lower()
    assert expected_query_substr.lower() in query_param, (
        f"Query parametar '{query_param}' ne sadrži '{expected_query_substr}' — "
        f"agent možda nije ispravno normalizovao typo."
    )


def test_no_hallucinated_empty_catalog_after_results():
    """Ako je search_products vratio non-empty rezultat, finalni reply
    NE smije sadržati 'nema dostupnih' / 'pretraga vratila prazno' /
    'nemamo u katalogu' — to je halucinacija (Sesija 8 production bug)."""
    result = run_agent([{"role": "user", "content": "Imate li laptop"}], "chat")

    # Mora imati search_products call sa rezultatima
    search_calls = [
        tc for tc in result["_trace"]["tool_calls"]
        if tc["tool_name"] == "search_products"
    ]
    assert search_calls, "Očekivan bar jedan search_products poziv"

    # Mora bar jedan vratiti non-empty rezultat (ne "Nema proizvoda...")
    has_results = any(
        "Nema proizvoda" not in tc["output_text"]
        and "prazan rezultat" not in tc["output_text"]
        for tc in search_calls
    )
    assert has_results, (
        f"Search_products nije vratio rezultate za 'laptop' — "
        f"katalog ima 50 laptopa u cat 98. Outputs: "
        f"{[tc['output_text'][:100] for tc in search_calls]}"
    )

    # Reply ne smije lagati o zalihama
    reply_lower = result["reply"].lower()
    forbidden = [
        "nema dostupnih laptop",
        "nemamo laptop",
        "pretraga je vratila prazn",
        "katalog ne sadrži laptop",
    ]
    for phrase in forbidden:
        assert phrase not in reply_lower, (
            f"HALUCINACIJA: reply sadrži '{phrase}' iako tool vratio rezultate.\n"
            f"Reply: {result['reply'][:400]!r}"
        )
