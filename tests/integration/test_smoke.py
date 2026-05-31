"""Smoke test — integration sloj sa TestClient + mock_llm (oba backenda)."""

import pytest

pytestmark = pytest.mark.integration


def test_healthz_returns_ok(test_client) -> None:
    resp = test_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_pwr_backend_routes_through_pwr(test_client, mock_llm, force_backend_pwr) -> None:
    """Default backend (PWR) — verifikuje PWR klijent zvan, Anthropic NIJE zvan."""
    resp = test_client.post(
        "/api/chat",
        json={"message": "test poruka", "history": []},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "ok"
    assert body["tool_calls"] == []
    assert body["iterations"] == 1
    assert mock_llm.pwr.chat.completions.create.called, "PWR klijent mora biti zvan"
    assert not mock_llm.anthropic.messages.create.called, (
        "Anthropic klijent NE smije biti zvan kad je backend=pwr (memorija "
        "llm_backend_pwr_imperative)"
    )


def test_chat_anthropic_fallback(test_client, mock_llm, force_backend_anthropic) -> None:
    """Fallback put — kad backend=anthropic, Anthropic klijent zvan, PWR ne."""
    resp = test_client.post("/api/chat", json={"message": "test", "history": []})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "ok"
    assert mock_llm.anthropic.messages.create.called
    assert not mock_llm.pwr.chat.completions.create.called


def test_chat_endpoint_rejects_empty_message(test_client) -> None:
    """Pydantic validation: message min_length=1."""
    resp = test_client.post("/api/chat", json={"message": "", "history": []})
    assert resp.status_code == 422
