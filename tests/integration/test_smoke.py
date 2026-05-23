"""Smoke test — integration sloj sa TestClient + mock Anthropic."""

import pytest

pytestmark = pytest.mark.integration


def test_healthz_returns_ok(test_client) -> None:
    resp = test_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_endpoint_returns_mock_reply(test_client, mock_anthropic) -> None:
    """Mock Anthropic vraća 'ok' default. Verifikuje da agent flow ne puca."""
    resp = test_client.post(
        "/api/chat",
        json={"message": "test poruka", "history": []},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "ok"
    assert body["tool_calls"] == []
    assert body["iterations"] == 1
    assert mock_anthropic.messages.create.called, "mora zvati mock, ne pravi API"


def test_chat_endpoint_rejects_empty_message(test_client) -> None:
    """Pydantic validation: message min_length=1."""
    resp = test_client.post("/api/chat", json={"message": "", "history": []})
    assert resp.status_code == 422
