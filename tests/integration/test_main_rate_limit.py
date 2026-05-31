"""Integration testovi za FastAPI rate-limit handler.

TDD RED faza — app/main.py nema exception handler-a za openai.RateLimitError
ili anthropic.RateLimitError, pa ih FastAPI guta kao 500 (memorija/EVAL_OPTIMIZACIJA
review). Eval client onda ne prepoznaje rate limit. GREEN faza dodaje handlere
koji mapiraju u 429 sa 'rate_limit' u body-ju.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.integration


def test_chat_returns_429_when_pwr_rate_limits(test_client, mock_llm, force_backend_pwr) -> None:
    """openai.RateLimitError iz _run_pwr → /api/chat 429 (ne 500)."""
    import openai

    req = MagicMock()
    resp = MagicMock(status_code=429, headers={}, request=req)
    mock_llm.pwr.chat.completions.create.side_effect = openai.RateLimitError(
        "rate_limit_exceeded",
        response=resp,
        body={"detail": "rate_limit_exceeded"},
    )
    response = test_client.post("/api/chat", json={"message": "x", "history": []})
    assert response.status_code == 429, (
        f"očekivao 429, dobio {response.status_code}; body={response.text[:200]}"
    )
    body = response.json()
    assert "rate_limit" in body.get("detail", "").lower()


def test_chat_returns_429_when_anthropic_rate_limits(
    test_client, mock_llm, force_backend_anthropic
) -> None:
    """anthropic.RateLimitError iz _run_anthropic → /api/chat 429."""
    import anthropic

    req = MagicMock()
    resp = MagicMock(status_code=429, headers={}, request=req)
    mock_llm.anthropic.messages.create.side_effect = anthropic.RateLimitError(
        "rate limited",
        response=resp,
        body={"error": {"type": "rate_limit_error"}},
    )
    response = test_client.post("/api/chat", json={"message": "x", "history": []})
    assert response.status_code == 429, (
        f"očekivao 429, dobio {response.status_code}; body={response.text[:200]}"
    )
    body = response.json()
    assert "rate_limit" in body.get("detail", "").lower()


def test_chat_500_for_other_errors_unchanged(mock_llm, force_backend_pwr) -> None:
    """Generične greške ostaju 500 (handleri samo hvataju rate-limit specifično).

    Koristi TestClient sa raise_server_exceptions=False da uhvati 500 response
    umjesto da exception bubble-uje van test-a (default Starlette TestClient
    raise-uje exception koji nije uhvaćen handler-om)."""
    from fastapi.testclient import TestClient

    from app.main import app

    mock_llm.pwr.chat.completions.create.side_effect = RuntimeError("boom")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/chat", json={"message": "x", "history": []})
    # FastAPI default za neuhvaćen Exception je 500. Ne smijemo to zamutiti.
    assert response.status_code == 500
