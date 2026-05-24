"""Empirijski budget tracker — sliding 5h window broja PWR poziva.

Cilj: Ralph ne pojede cijelu PWR sesiju u jednoj iteraciji. Eval runner
prije svakog poziva provjeri `should_pause`; ako True → snima checkpoint,
exit kod 3, ralph.sh pauzira do reseta.

Default `MAX_CALLS=80` u 5h prozoru × threshold `0.65` = pause na 52 poziva.
Korisnik je 2026-05-24 odabrao 80 kao početnu konzervativnu procjenu;
kalibracija na osnovu prvih nekoliko rate-limit/budget hit-ova.

State: `<cache_dir>/pwr_calls.jsonl` — append-only log, jedan ts po liniji.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

DEFAULT_MAX_CALLS: int = 80
DEFAULT_THRESHOLD: float = 0.65
WINDOW_SECONDS: int = 5 * 3600  # 5h sliding window


def _log_path(cache_dir: Path) -> Path:
    return cache_dir / "pwr_calls.jsonl"


def record_call(cache_dir: Path, timestamp: float | None = None) -> None:
    """Append jedan call timestamp u pwr_calls.jsonl.

    Kreira cache_dir ako ne postoji. `timestamp=None` koristi `time.time()`.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp if timestamp is not None else time.time()
    log = _log_path(cache_dir)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts}) + "\n")


def count_calls_last_5h(cache_dir: Path, now: float | None = None) -> int:
    """Broj poziva u posljednjih 5h od `now` (default `time.time()`).

    Defensive: vraća 0 ako log fajl ne postoji ili je corrupted.
    Corrupted JSON redovi se skipuju, ostali se broje.
    """
    log = _log_path(cache_dir)
    if not log.exists():
        return 0
    now_ts = now if now is not None else time.time()
    cutoff = now_ts - WINDOW_SECONDS
    count = 0
    with log.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("ts", 0) >= cutoff:
                count += 1
    return count


def should_pause(
    cache_dir: Path,
    now: float | None = None,
    max_calls: int = DEFAULT_MAX_CALLS,
    threshold: float = DEFAULT_THRESHOLD,
) -> bool:
    """True ako broj poziva u 5h prozoru ≥ max_calls × threshold.

    Default: 80 × 0.65 = 52 poziva → pause. Korisnik tweakuje preko
    `--max-calls` CLI arg ili `max_calls` parametra u run_suite.
    """
    count = count_calls_last_5h(cache_dir, now)
    return count >= int(max_calls * threshold)
