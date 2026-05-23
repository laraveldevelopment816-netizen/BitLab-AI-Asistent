"""Pytest fixtures za bitlab-ai-asistent test pyramide.

Glavni invariant (memorija anthropic_budget): nijedan test NE SMIJE zvati pravi
Anthropic API. `mock_anthropic` fixture monkey-patch-uje `app.agent._get_client`
i `app.agent._client` da vraćaju lažni klijent sa kontrolisanim odgovorom.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


def _make_text_response(text: str = "ok", stop_reason: str = "end_turn") -> MagicMock:
    """Konstruiše Anthropic-shaped response sa jednim text blokom."""
    block = MagicMock()
    block.text = text
    block.type = "text"
    response = MagicMock()
    response.content = [block]
    response.stop_reason = stop_reason
    return response


@pytest.fixture
def mock_anthropic(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock anthropic.Anthropic — vraća deterministic dummy odgovor.

    Test može dalje konfigurisati:
        mock_anthropic.messages.create.return_value = my_custom_response
    """
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _make_text_response("ok")

    def _get_fake_client() -> Any:
        return fake_client

    monkeypatch.setattr("app.agent._get_client", _get_fake_client)
    monkeypatch.setattr("app.agent._client", fake_client)
    return fake_client


@pytest.fixture
def make_response():
    """Helper da test kreira custom Anthropic response.

    Primjer:
        mock_anthropic.messages.create.return_value = make_response("hej")
    """
    return _make_text_response


@pytest.fixture
def test_client(mock_anthropic: MagicMock):  # noqa: ARG001 — fixture dependency
    """FastAPI TestClient sa mock-ovanim Anthropic-om. Za integration testove."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
