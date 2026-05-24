"""Helper koji ralph.sh poziva između iteracija ako PAUSE marker postoji.

PAUSE marker shape (jedan fajl `ralph/PAUSE`):
- Prazan / bez `until=` linije → cooperative wait, čekaj dok korisnik ručno `rm`.
- `until=<epoch>` → auto-resume kad sada >= epoch (helper sam briše marker).

Poll svakih 300s (PAUSE_POLL_SECONDS env override za testove).

Exit kodovi:
- 0 — pauza okončana, ralph.sh nastavlja sljedeću iteraciju.
- 1 — STOP marker pronađen tokom čekanja, ralph.sh treba da exit-uje.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path


def parse_until(content: str) -> float | None:
    """Vrati epoch iz 'until=<epoch>' linije, None ako prazan/whitespace/invalid."""
    if not content or not content.strip():
        return None
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("until="):
            value = line[len("until=") :].strip()
            try:
                return float(value)
            except ValueError:
                return None
    return None


def wait_for_resume(
    pause_file: Path,
    stop_file: Path,
    now_fn: Callable[[], float] = time.time,
    sleep_fn: Callable[[float], None] = time.sleep,
    poll_interval: int | None = None,
) -> int:
    """Pauziraj dok PAUSE marker ne nestane (cooperative) ili dok until ne istekne (auto).

    Return 0 = nastavi normalno. Return 1 = STOP marker, forsiraj exit.
    """
    if poll_interval is None:
        poll_interval = int(os.getenv("PAUSE_POLL_SECONDS", "300"))

    while True:
        if stop_file.exists():
            return 1
        if not pause_file.exists():
            return 0
        content = pause_file.read_text(encoding="utf-8")
        until = parse_until(content)
        if until is not None and now_fn() >= until:
            pause_file.unlink(missing_ok=True)
            return 0
        sleep_fn(poll_interval)


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    pause = project_root / "ralph" / "PAUSE"
    stop = project_root / "ralph" / "STOP"
    return wait_for_resume(pause_file=pause, stop_file=stop)


if __name__ == "__main__":
    sys.exit(main())
