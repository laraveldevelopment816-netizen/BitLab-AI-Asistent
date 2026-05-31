"""Procjena PWR sesija reset epoch-a.

ralph.sh poziva ovaj helper kad runner exit-uje sa kodom 3 — koristi
najstariji unos iz `~/.cache/bitlab-ralph/pwr_calls.jsonl` plus 5h kao
procjenu kada sliding window oslobađa kvotu.

Fallback: now + 5h ako log ne postoji ili je prazan.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

WINDOW_SECONDS: int = 5 * 3600


def _default_log_path() -> Path:
    return Path.home() / ".cache" / "bitlab-ralph" / "pwr_calls.jsonl"


def estimate_reset(
    log_path: Path | None = None,
    now_fn: Callable[[], float] = time.time,
) -> int:
    """Vrati epoch (int) kada sliding 5h prozor oslobađa najstariji poziv.

    Defensive: log fajl koji ne postoji ili je prazan → now + 5h fallback.
    Corrupted JSON redovi se skipuju.
    """
    if log_path is None:
        log_path = _default_log_path()
    if not log_path.exists():
        return int(now_fn() + WINDOW_SECONDS)

    oldest: float | None = None
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("ts")
            if not isinstance(ts, int | float):
                continue
            if oldest is None or ts < oldest:
                oldest = float(ts)

    if oldest is None:
        return int(now_fn() + WINDOW_SECONDS)
    return int(oldest + WINDOW_SECONDS)


def main() -> int:
    print(estimate_reset())
    return 0


if __name__ == "__main__":
    sys.exit(main())
