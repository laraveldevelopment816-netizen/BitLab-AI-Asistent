"""Unit testovi za evals/framework/errors.py — custom exceptions.

TDD RED faza — modul još ne postoji, import fail. GREEN faza dodaje
evals/framework/errors.py sa RateLimitDetected klasom.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_rate_limit_detected_is_exception() -> None:
    """RateLimitDetected mora biti Exception subclass koji se da raise-ovati."""
    from evals.framework.errors import RateLimitDetected

    assert issubclass(RateLimitDetected, Exception)
    with pytest.raises(RateLimitDetected, match="test message"):
        raise RateLimitDetected("test message")


def test_rate_limit_detected_preserves_message() -> None:
    """Exception poruka mora biti dostupna kroz str() — runner je propusti u log."""
    from evals.framework.errors import RateLimitDetected

    try:
        raise RateLimitDetected("PWR session limit reached")
    except RateLimitDetected as e:
        assert "PWR session limit reached" in str(e)
