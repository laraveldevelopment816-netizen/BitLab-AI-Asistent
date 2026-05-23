"""TypedDict-ovi za eval entry, tool call, verdict.

Schema invariant (memorija test_case_invariant): entry struktura se NE mijenja
kad refaktorišemo runner — entry je SSOT, runner se prilagođava.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class ToolCall(TypedDict):
    """Šta je Claude zaista pozvao."""

    name: str
    args: dict[str, Any]


class HistoryMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class ExpectClause(TypedDict, total=False):
    """Šta entry očekuje. Sva polja opciona — entry navodi samo ono što testira.

    Konvencije:
    - `tool=None` (eksplicitan key sa None): negativni entry, NIJEDAN tool ne smije.
    - `tool` izostavljen: routing nije validovan, samo result.
    - `args_subset`: subset matching nad args dict-om.
    - `args_query_contains`: substring match nad args.query (case-insensitive).
    - `min_results`: za result fazu, broj proizvoda u tool response (Faza 2+).
    - `top_result_contains_any`: bar jedan string iz liste mora biti u top rezultatu.
    """

    tool: str | None
    args_subset: dict[str, Any]
    args_query_contains: str
    min_results: int
    top_result_contains_any: list[str]


class EvalEntry(TypedDict, total=False):
    """Jedan red u evals/sets/<suite>.jsonl. id, query, expect su obavezni."""

    id: str
    query: str
    history: list[HistoryMessage]
    expect: ExpectClause
    tags: list[str]


Verdict = Literal["PASS", "FAIL", "WARN", "NA"]


class EvalVerdict(TypedDict):
    """Rezultat jednog entry-ja kroz judge pipeline."""

    entry_id: str
    routing: Verdict
    result: Verdict
    overall: Verdict
    actual_tool_calls: list[ToolCall]
    reply: str
    iterations: int
    error: str | None
    elapsed_ms: int
