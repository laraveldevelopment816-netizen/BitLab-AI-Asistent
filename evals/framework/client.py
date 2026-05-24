"""HTTP klijent ka FastAPI /api/chat — koristi se iz runner.py."""

from __future__ import annotations

from typing import Any

import httpx

from .types import HistoryMessage


def call_chat(
    base_url: str,
    query: str,
    history: list[HistoryMessage],
    timeout: float = 120.0,
) -> dict[str, Any]:
    """POST {base_url}/api/chat. Vraća parsed JSON body.

    Očekuje shape `{reply: str, tool_calls: list, iterations: int}` (vidi app/agent.py:run_agent).
    Diže HTTPError ako server vraća non-2xx.
    """
    payload = {"message": query, "history": history}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()
