"""Unit: SYSTEM_PROMPT_V1 konstanta + proslijeđena u OBA runnera.

Acceptance task "Sistem prompt v1 u oba runnera" iz ralph/IMPLEMENTATION_PLAN.md:
- Konstanta definisana u app/agent.py (single source — nije inline u runnerima).
- Konstanta nije prazna i ima minimum semantičkog sadržaja (pomenuti oba toola).
- _run_anthropic prosljeđuje konstanu kao `system=` parametar.
- _run_pwr prosljeđuje konstantu kao prvu poruku {role:"system", content:...}.

Invariant (memorija anthropic_budget): testovi koriste mock_llm fixture — bez
stvarnih HTTP poziva ka PWR ili Anthropic API-ju.
"""

from __future__ import annotations

import pytest

from app.agent import SYSTEM_PROMPT_V1, run_agent

pytestmark = pytest.mark.unit


def test_system_prompt_v1_constant_defined_and_nonempty() -> None:
    """Konstanta postoji kao string i nije prazna ni samo whitespace."""
    assert isinstance(SYSTEM_PROMPT_V1, str)
    assert SYSTEM_PROMPT_V1.strip(), "SYSTEM_PROMPT_V1 ne smije biti prazan"
    # Sanity: prompt mora nominalno imenovati oba toola, inače rutiranje neće raditi.
    assert "category_overview" in SYSTEM_PROMPT_V1
    assert "search_products" in SYSTEM_PROMPT_V1


def test_system_prompt_v1_passed_to_anthropic_runner(mock_llm, force_backend_anthropic) -> None:
    """_run_anthropic prosljeđuje konstantu kroz `system=` parametar."""
    run_agent([{"role": "user", "content": "Računari"}])

    assert mock_llm.anthropic.messages.create.called
    call_kwargs = mock_llm.anthropic.messages.create.call_args_list[0].kwargs
    assert call_kwargs.get("system") == SYSTEM_PROMPT_V1
    # PWR runner ne smije biti pogođen kad je backend anthropic.
    assert not mock_llm.pwr.chat.completions.create.called


def test_system_prompt_v1_passed_to_pwr_runner(mock_llm, force_backend_pwr) -> None:
    """_run_pwr prosljeđuje konstantu kao prvu poruku {role:'system', content:...}."""
    run_agent([{"role": "user", "content": "Računari"}])

    assert mock_llm.pwr.chat.completions.create.called
    call_kwargs = mock_llm.pwr.chat.completions.create.call_args_list[0].kwargs
    messages = call_kwargs.get("messages", [])
    assert len(messages) >= 1, "PWR mora dobiti barem system poruku + user"
    first = messages[0]
    assert first["role"] == "system"
    assert first["content"] == SYSTEM_PROMPT_V1
    # Anthropic runner ne smije biti pogođen kad je backend pwr.
    assert not mock_llm.anthropic.messages.create.called
