"""Integration: tool dispatch kroz PWR i Anthropic backend, bez mreže.

Provjera spec specs/categories.md §3.1 — `category_overview` tool mora biti
dispatch-ovan u OBA runnera, a `tool_calls` u response shape-u mora odražavati
poziv (`{name, args}`) tako da eval framework može da poredi sa očekivanjima
iz `evals/sets/categories.jsonl`.

Invariant (memorija anthropic_budget + ralph/AGENTS.md): nijedan test ne smije
zvati pravi LLM. Sve ide kroz `mock_llm` fixture.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.integration


def _pwr_tool_call_response(name: str, arguments: str, call_id: str = "call_1") -> MagicMock:
    """OpenAI-shape response sa jednim tool_call blokom (finish_reason='tool_calls').

    Eksplicitno setujemo `tc.type = "function"` — MagicMock inače auto-kreira
    novi MagicMock pri pristupu atributu, što razbija runtime tag check u
    _run_pwr (`getattr(tc, "type", ...) == "function"`).
    """
    tc = MagicMock()
    tc.id = call_id
    tc.type = "function"
    tc.function.name = name
    tc.function.arguments = arguments

    message = MagicMock()
    message.content = None
    message.tool_calls = [tc]

    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "tool_calls"

    response = MagicMock()
    response.choices = [choice]
    return response


def _pwr_final_response(text: str) -> MagicMock:
    """OpenAI-shape final text response (finish_reason='stop')."""
    message = MagicMock()
    message.content = text
    message.tool_calls = []
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = "stop"
    response = MagicMock()
    response.choices = [choice]
    return response


def _anthropic_tool_use_response(name: str, args: dict, tool_use_id: str = "toolu_1") -> MagicMock:
    """Anthropic-shape response sa tool_use blokom (stop_reason='tool_use')."""
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_use_id
    block.name = name
    block.input = args
    # spec block bez .text — hasattr provjera u runneru ovo skipuje
    del block.text

    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    return response


def _anthropic_final_response(text: str) -> MagicMock:
    """Anthropic-shape final text response (stop_reason='end_turn')."""
    block = MagicMock()
    block.text = text
    block.type = "text"
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    return response


def test_category_overview_dispatched_through_pwr(test_client, mock_llm, force_backend_pwr) -> None:
    """PWR put: model traži category_overview, runner dispatchuje + kapsulira poziv.

    Acceptance task #1 iz ralph/IMPLEMENTATION_PLAN.md: prvi parent entry
    (`cat-parent-17` query 'Računari') → eval routing PASS očekuje
    `tool_calls == [{name: 'category_overview', args: {category_id: 17}}]`.
    """
    mock_llm.pwr.chat.completions.create.side_effect = [
        _pwr_tool_call_response("category_overview", '{"category_id": 17}'),
        _pwr_final_response("Pregled potkategorija za Računari."),
    ]

    resp = test_client.post("/api/chat", json={"message": "Računari", "history": []})
    assert resp.status_code == 200
    body = resp.json()

    assert body["tool_calls"] == [{"name": "category_overview", "args": {"category_id": 17}}]
    assert body["iterations"] == 2
    assert body["reply"] == "Pregled potkategorija za Računari."

    # PWR put aktiviran 2x (initial + after tool_result), Anthropic NIJE zvan.
    assert mock_llm.pwr.chat.completions.create.call_count == 2
    assert not mock_llm.anthropic.messages.create.called

    # Tool definicije proslijeđene modelu u OpenAI shape (verifikacija dispatch-a).
    first_call_kwargs = mock_llm.pwr.chat.completions.create.call_args_list[0].kwargs
    assert "tools" in first_call_kwargs
    tool_names = {t["function"]["name"] for t in first_call_kwargs["tools"]}
    assert "category_overview" in tool_names


def test_category_overview_dispatched_through_anthropic(
    test_client, mock_llm, force_backend_anthropic
) -> None:
    """Anthropic fallback put: ista semantika kao PWR — tool_calls kapsuliran isto."""
    mock_llm.anthropic.messages.create.side_effect = [
        _anthropic_tool_use_response("category_overview", {"category_id": 17}),
        _anthropic_final_response("Pregled potkategorija za Računari."),
    ]

    resp = test_client.post("/api/chat", json={"message": "Računari", "history": []})
    assert resp.status_code == 200
    body = resp.json()

    assert body["tool_calls"] == [{"name": "category_overview", "args": {"category_id": 17}}]
    assert body["iterations"] == 2
    assert body["reply"] == "Pregled potkategorija za Računari."
    assert mock_llm.anthropic.messages.create.call_count == 2
    assert not mock_llm.pwr.chat.completions.create.called

    # Tool definicije proslijeđene modelu u Anthropic shape.
    first_call_kwargs = mock_llm.anthropic.messages.create.call_args_list[0].kwargs
    assert "tools" in first_call_kwargs
    tool_names = {t["name"] for t in first_call_kwargs["tools"]}
    assert "category_overview" in tool_names


def test_category_overview_handler_returns_children() -> None:
    """Unit-level provjera: handler stub vraća djecu parent kategorije iz JSON-a.

    cat_id=17 (Računari) ima više djece u data/categories_new.json (vidi
    parent_id=17 entry-je). Handler mora ih sve uključiti u `children` listu.
    """
    import json as _json

    from app.tools import dispatch

    result_str = dispatch("category_overview", {"category_id": 17})
    payload = _json.loads(result_str)

    assert payload["category_id"] == 17
    assert isinstance(payload["children"], list)
    assert len(payload["children"]) >= 2, "cat_id=17 mora imati ≥2 djece"
    for child in payload["children"]:
        assert "id" in child
        assert "name" in child


def test_dispatch_unknown_tool_returns_error_payload() -> None:
    """Unknown tool → JSON error payload, runner ne crash-uje."""
    import json as _json

    from app.tools import dispatch

    result_str = dispatch("nonexistent_tool", {})
    payload = _json.loads(result_str)
    assert "error" in payload
