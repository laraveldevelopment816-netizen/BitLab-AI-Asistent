"""HTTP klijent ka FastAPI /api/chat — koristi se iz runner.py.

429 response se specijalizuje u `RateLimitDetected` da runner može
gracefully da snima checkpoint umjesto da entry tretira kao generičan FAIL.
"""

from __future__ import annotations

from typing import Any

import httpx

from .errors import RateLimitDetected
from .types import HistoryMessage


def call_chat(
    base_url: str,
    query: str,
    history: list[HistoryMessage],
    timeout: float = 120.0,
) -> dict[str, Any]:
    """POST {base_url}/api/chat. Vraća parsed JSON body.

    - 2xx → parsed JSON ({reply, tool_calls, iterations}).
    - 429 → diže `RateLimitDetected` (specijalan signal za runner checkpoint).
    - drugi non-2xx → diže `httpx.HTTPStatusError` (generic).
    """
    payload = {"message": query, "history": history}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
        if resp.status_code == 429:
            detail = _extract_detail(resp)
            raise RateLimitDetected(f"HTTP 429: {detail}")
        resp.raise_for_status()
        return resp.json()


def _extract_detail(resp: httpx.Response) -> str:
    """Pokušaj parse JSON body.detail, fallback na text snippet."""
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except Exception:  # noqa: BLE001 — JSON može biti malformed
        pass
    return resp.text[:200]
