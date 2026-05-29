"""
Unit testovi za centralne FastAPI exception handler-e za Anthropic SDK greške
(STATUS kartica c4xh).

Pokrivaju 4 error scenarija + happy path regression:
- AuthenticationError (401) — neuhvaćeno u agent.py, bubble do central handler-a → 503
- InternalServerError (5xx Anthropic-side) → 503
- Quota error (`credit balance` / `billing` u poruci) → 402 + eskalacija (tel/email)
- APIConnectionError (mreža) → 503 sa porukom o mreži
- Happy path: kad run_agent vrati uspješan rezultat, handler ne interferira → 200

Test ne zove pravi Anthropic API (mock-uje `app.agent.run_agent`); ne treba
`anthropic_api` marker.
"""
from __future__ import annotations

import os

# Settings validator zahtijeva ANTHROPIC_API_KEY prije import-a app.main.
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test")

from unittest.mock import patch

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    # raise_server_exceptions=False — vrati HTTP response umjesto re-raise-a
    # (testiramo upravo da handler hvata exception umjesto da bubble-uje).
    return TestClient(app, raise_server_exceptions=False)


def _req():
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _status_error(status_code: int, message: str) -> anthropic.APIStatusError:
    resp = httpx.Response(status_code=status_code, request=_req(), text=message)
    return anthropic.APIStatusError(message, response=resp, body={"error": {"message": message}})


def _auth_error(message: str = "Invalid API key") -> anthropic.AuthenticationError:
    resp = httpx.Response(status_code=401, request=_req(), text=message)
    return anthropic.AuthenticationError(message, response=resp, body={"error": {"message": message}})


def _internal_error(message: str = "Upstream provider error") -> anthropic.InternalServerError:
    resp = httpx.Response(status_code=500, request=_req(), text=message)
    return anthropic.InternalServerError(message, response=resp, body={"error": {"message": message}})


def _connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=_req())


def _post_chat(client: TestClient, run_agent_exc: BaseException):
    """POST /api/chat sa mock-om koji forsira run_agent da raise-uje exc."""
    with patch("app.agent.run_agent", side_effect=run_agent_exc):
        return client.post("/api/chat", json={"message": "test", "history": []})


class TestAnthropicCentralHandler:
    def test_authentication_error_returns_503(self, client):
        r = _post_chat(client, _auth_error())
        assert r.status_code == 503
        body = r.json()
        assert body["error"] == "ai_unavailable"
        assert "AI servis privremeno nije dostupan" in body["reply"]
        assert "066 516 174" in body["reply"]

    def test_internal_server_error_returns_503(self, client):
        r = _post_chat(client, _internal_error())
        assert r.status_code == 503
        assert r.json()["error"] == "ai_unavailable"

    def test_quota_credit_balance_returns_402_with_escalation(self, client):
        exc = _status_error(400, "Your credit balance is too low to access the Claude API.")
        r = _post_chat(client, exc)
        assert r.status_code == 402
        body = r.json()
        assert body["error"] == "ai_quota_exhausted"
        assert "066 516 174" in body["reply"]
        assert "prodaja@bitlab.rs" in body["reply"]

    def test_quota_billing_keyword_also_triggers_402(self, client):
        """Heuristika prepoznaje `billing` jednako kao `credit balance`."""
        exc = _status_error(400, "Account billing issue")
        r = _post_chat(client, exc)
        assert r.status_code == 402
        assert r.json()["error"] == "ai_quota_exhausted"

    def test_quota_keyword_also_triggers_402(self, client):
        """Heuristika prepoznaje i `quota` ključnu riječ."""
        exc = _status_error(429, "You have exceeded your quota for this period.")
        r = _post_chat(client, exc)
        assert r.status_code == 402
        assert r.json()["error"] == "ai_quota_exhausted"

    def test_connection_error_returns_503_with_network_message(self, client):
        r = _post_chat(client, _connection_error())
        assert r.status_code == 503
        body = r.json()
        assert body["error"] == "ai_unavailable"
        assert "mre" in body["reply"].lower()  # "Mreža" / "mreža"

    def test_happy_path_unaffected_by_handlers(self, client):
        """Kad nema exception-a, /api/chat vraća uobičajeni 200 ChatResponse."""
        fake_result = {
            "reply": "Zdravo!",
            "reply_voice": "Zdravo.",
            "tools_used": [],
            "escalated": False,
            "iterations": 1,
            "_trace": {"model": "claude-sonnet-4-6"},
        }
        with patch("app.agent.run_agent", return_value=fake_result), \
             patch("app.server.dashboard._persist_trace", return_value=None):
            r = client.post("/api/chat", json={"message": "test", "history": []})
        assert r.status_code == 200
        assert r.json()["reply"] == "Zdravo!"
