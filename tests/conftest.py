"""Pytest fixtures za bitlab-ai-asistent test pyramide.

Glavni invariant (memorija anthropic_budget): nijedan test NE SMIJE zvati ni
PWR backend ni pravi Anthropic API. `mock_llm` fixture mock-uje OBA klijenta
(_anthropic_client + _pwr_client), pa bilo koju LLM_BACKEND odluku Ralph ili
korisnik napravi, testovi nikad ne idu na mrežu.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _make_anthropic_response(text: str = "ok", stop_reason: str = "end_turn") -> MagicMock:
    """Anthropic-shaped response sa jednim text blokom."""
    block = MagicMock()
    block.text = text
    block.type = "text"
    response = MagicMock()
    response.content = [block]
    response.stop_reason = stop_reason
    return response


def _make_pwr_response(text: str = "ok", finish_reason: str = "stop") -> MagicMock:
    """OpenAI-shaped response (PWR backend) sa jednom choice porukom."""
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def mock_llm(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock OBA LLM klijenta — bez stvarnih HTTP poziva.

    Vraća holder sa `.anthropic` i `.pwr` atributima. Test može konfigurisati:
        mock_llm.anthropic.messages.create.return_value = ...
        mock_llm.pwr.chat.completions.create.return_value = ...
    """
    fake_anthropic = MagicMock()
    fake_anthropic.messages.create.return_value = _make_anthropic_response("ok")

    fake_pwr = MagicMock()
    fake_pwr.chat.completions.create.return_value = _make_pwr_response("ok")

    monkeypatch.setattr("app.agent._get_anthropic_client", lambda: fake_anthropic)
    monkeypatch.setattr("app.agent._get_pwr_client", lambda: fake_pwr)
    monkeypatch.setattr("app.agent._anthropic_client", fake_anthropic)
    monkeypatch.setattr("app.agent._pwr_client", fake_pwr)

    holder = MagicMock()
    holder.anthropic = fake_anthropic
    holder.pwr = fake_pwr
    return holder


@pytest.fixture
def force_backend_pwr(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forsiraj LLM_BACKEND=pwr + dummy PWR_API_KEY u settings."""
    monkeypatch.setattr("app.config.settings.llm_backend", "pwr")
    monkeypatch.setattr("app.config.settings.pwr_api_key", "test-key")


@pytest.fixture
def force_backend_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forsiraj LLM_BACKEND=anthropic put (fallback)."""
    monkeypatch.setattr("app.config.settings.llm_backend", "anthropic")


@pytest.fixture
def make_response():
    """Helper za custom Anthropic ili PWR response shape u testovima."""
    return {
        "anthropic": _make_anthropic_response,
        "pwr": _make_pwr_response,
    }


@pytest.fixture
def test_client(mock_llm):  # noqa: ARG001 — mock_llm mora biti aktivan prije TestClient-a
    """FastAPI TestClient sa mock-ovanim OBA LLM klijenta."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
