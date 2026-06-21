"""Unit testovi za evals/framework/client.py — 429 → RateLimitDetected propagacija.

TDD RED faza — client trenutno samo `raise_for_status()` što baca httpx.HTTPStatusError.
GREEN faza specijalizuje 429 u RateLimitDetected da runner može gracefully da snima
checkpoint.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

pytestmark = pytest.mark.unit


def _make_fake_client(response: httpx.Response) -> MagicMock:
    """Helper: MagicMock context manager koji vraća fiksiran response na .post()."""
    fake = MagicMock()
    fake.__enter__ = MagicMock(return_value=fake)
    fake.__exit__ = MagicMock(return_value=False)
    fake.post = MagicMock(return_value=response)
    return fake


def test_client_raises_rate_limit_on_429(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 429 → RateLimitDetected (ne httpx.HTTPStatusError generičan)."""
    from evals.framework import client
    from evals.framework.errors import RateLimitDetected

    req = httpx.Request("POST", "http://mock/api/chat")
    response = httpx.Response(429, json={"detail": "rate_limit: PWR"}, request=req)
    monkeypatch.setattr("httpx.Client", lambda **k: _make_fake_client(response))

    with pytest.raises(RateLimitDetected, match="rate_limit"):
        client.call_chat("http://mock", "x", [])


def test_client_propagates_non_429_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Druge HTTP greške (500, 503) ostaju httpx.HTTPStatusError (ne RateLimitDetected)."""
    from evals.framework import client
    from evals.framework.errors import RateLimitDetected

    req = httpx.Request("POST", "http://mock/api/chat")
    response = httpx.Response(500, json={"detail": "internal error"}, request=req)
    monkeypatch.setattr("httpx.Client", lambda **k: _make_fake_client(response))

    with pytest.raises(httpx.HTTPStatusError):
        client.call_chat("http://mock", "x", [])
    # Verifikuj da 500 NIJE pogrešno klasifikovan kao rate limit.
    try:
        client.call_chat("http://mock", "x", [])
    except RateLimitDetected:
        pytest.fail("500 ne smije biti RateLimitDetected")
    except httpx.HTTPStatusError:
        pass  # očekivano


def test_client_returns_body_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """2xx response normalno vraća parsed JSON (regression — ne dirati happy path)."""
    from evals.framework import client

    req = httpx.Request("POST", "http://mock/api/chat")
    response = httpx.Response(
        200, json={"reply": "ok", "tool_calls": [], "iterations": 1}, request=req
    )
    monkeypatch.setattr("httpx.Client", lambda **k: _make_fake_client(response))

    body = client.call_chat("http://mock", "x", [])
    assert body["reply"] == "ok"
