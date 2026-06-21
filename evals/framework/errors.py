"""Custom exceptions za eval framework.

`RateLimitDetected` se diže iz `client.call_chat` kad backend (PWR ili
Anthropic) signalizira rate limit (HTTP 429). Runner ga hvata posebno
od generičnih grešaka da bi gracefully snimio checkpoint pa exit-ovao
sa specifičnim kodom 3 — ralph.sh detektuje kod 3 i pauzira do reseta.
"""

from __future__ import annotations


class RateLimitDetected(Exception):
    """Backend rate limit hit — snima checkpoint, exit code 3."""
