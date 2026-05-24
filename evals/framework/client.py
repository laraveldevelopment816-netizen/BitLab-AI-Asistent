"""HTTP klijent ka FastAPI /api/chat — koristi se iz runner.py."""

from __future__ import annotations

from typing import Any

import httpx

from .types import HistoryMessage

_RATE_LIMIT_PHRASES = (
    "rate_limit",
    "rate limit",
    "usage limit",
    "overloaded",
    "too many requests",
)


class RateLimitError(Exception):
    """PWR sesija iscrpila limit — čekaj reset."""


def call_chat(
    base_url: str,
    query: str,
    history: list[HistoryMessage],
    timeout: float = 120.0,
) -> dict[str, Any]:
    """POST {base_url}/api/chat. Vraća parsed JSON body.

    Diže RateLimitError ako server signalizira iscrpljeni limit (429 ili
    5xx sa prepoznatljivim porukom). Diže HTTPError za ostale greške.
    """
    payload = {"message": query, "history": history}
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{base_url.rstrip('/')}/api/chat", json=payload)
        if resp.status_code == 429:
            raise RateLimitError(f"HTTP 429: {resp.text[:200]}")
        if resp.status_code >= 500:
            body_lower = resp.text.lower()
            if any(phrase in body_lower for phrase in _RATE_LIMIT_PHRASES):
                raise RateLimitError(
                    f"HTTP {resp.status_code} rate limit signal: {resp.text[:200]}"
                )
        resp.raise_for_status()
        return resp.json()
