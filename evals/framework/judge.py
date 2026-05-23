"""Parser-based judge — deterministički, bez LLM.

3 sloja verdict-a:
- `verdict_routing`: da li je Claude pozvao očekivani tool sa očekivanim args?
- `verdict_result`: da li je tool vratio očekivane podatke? (Faza 2+ za RAG.)
- `verdict_overall`: sjedinjuje routing + result u jedan top-line signal.

Sve funkcije su pure (input → output, no side effects) → trivijalne za unit test.
"""

from __future__ import annotations

from typing import Any

from .types import EvalEntry, ToolCall, Verdict


def verdict_routing(entry: EvalEntry, actual_tool_calls: list[ToolCall]) -> Verdict:
    """Da li je Claude pozvao očekivani tool?

    PASS — bar jedan tool call ima ime == expected.tool i args ⊇ expected.args_subset.
    FAIL — drugačiji tool zvan, ili tool nije zvan kad jeste očekivan,
           ili tool zvan kad expect.tool=None (negativan entry).
    NA   — entry nema 'tool' u expect (samo result se provjerava).
    """
    expect = entry["expect"]

    if "tool" not in expect:
        return "NA"

    expected_tool = expect.get("tool")

    if expected_tool is None:
        return "PASS" if not actual_tool_calls else "FAIL"

    expected_args = expect.get("args_subset", {})
    for call in actual_tool_calls:
        if call["name"] == expected_tool and _args_subset_match(expected_args, call["args"]):
            return "PASS"
    return "FAIL"


def verdict_result(entry: EvalEntry, actual_tool_calls: list[ToolCall], reply: str) -> Verdict:
    """Da li su tool rezultati i reply tačni?

    Trenutno podržano (Faza 0/1):
    - `args_query_contains`: actual call args.query mora sadržati substring (CI).
    - `min_results` / `top_result_contains_any`: WARN dok RAG nije u Fazi 2.

    Vraća NA ako expect nema ni jedno result polje.
    """
    expect = entry["expect"]
    result_keys = {"args_query_contains", "min_results", "top_result_contains_any"}
    if not (expect.keys() & result_keys):
        return "NA"

    if "args_query_contains" in expect:
        needle = str(expect["args_query_contains"]).lower()
        found = any(
            needle in str(call["args"].get("query", "")).lower() for call in actual_tool_calls
        )
        if not found:
            return "FAIL"

    if expect.keys() & {"min_results", "top_result_contains_any"}:
        return "WARN"

    return "PASS"


def verdict_overall(routing: Verdict, result: Verdict) -> Verdict:
    """Sjedinjuje routing + result u top-line PASS/FAIL/WARN/NA.

    Logika:
    - Bilo koji FAIL → FAIL (najjači signal).
    - Bilo koji WARN i nema FAIL → WARN.
    - PASS i (PASS ili NA) → PASS.
    - Samo NA (oboje) → NA (entry zapravo ništa ne testira — vjerovatno greška).
    """
    if "FAIL" in (routing, result):
        return "FAIL"
    if "WARN" in (routing, result):
        return "WARN"
    if routing == "NA" and result == "NA":
        return "NA"
    return "PASS"


def _args_subset_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """actual mora sadržati sve expected key-eve sa istim vrijednostima."""
    for key, value in expected.items():
        if key not in actual:
            return False
        if actual[key] != value:
            return False
    return True
