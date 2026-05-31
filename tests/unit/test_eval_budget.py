"""Unit testovi za evals/framework/budget.py — empirijski call counter + sliding window.

TDD RED faza — modul ne postoji. GREEN faza dodaje `record_call`,
`count_calls_last_5h`, `should_pause`.

Default `MAX_CALLS=80` u 5h prozoru × threshold `0.65` = pause na 52 poziva
(po dogovoru sa korisnikom, 2026-05-24; kalibracija na osnovu prve sesije).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# --------------------------- record_call + count ---------------------------


def test_record_call_creates_log_with_timestamp(tmp_path: Path) -> None:
    """record_call kreira pwr_calls.jsonl u cache_dir sa jednim redom (ts polje)."""
    from evals.framework import budget

    budget.record_call(tmp_path, timestamp=1000.0)
    log = tmp_path / "pwr_calls.jsonl"
    assert log.exists()
    content = log.read_text(encoding="utf-8").strip()
    assert '"ts": 1000.0' in content or '"ts":1000' in content


def test_record_call_appends_multiple_times(tmp_path: Path) -> None:
    """Više record_call poziva → više redova u log-u."""
    from evals.framework import budget

    budget.record_call(tmp_path, timestamp=1000.0)
    budget.record_call(tmp_path, timestamp=2000.0)
    budget.record_call(tmp_path, timestamp=3000.0)
    log = tmp_path / "pwr_calls.jsonl"
    lines = log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3


def test_record_call_creates_directory_if_missing(tmp_path: Path) -> None:
    """Cache dir koji ne postoji se kreira pri prvom record_call-u."""
    from evals.framework import budget

    new_dir = tmp_path / "new_budget"
    assert not new_dir.exists()
    budget.record_call(new_dir, timestamp=1000.0)
    assert new_dir.exists()


def test_count_returns_zero_when_log_missing(tmp_path: Path) -> None:
    """Bez log fajla → count 0 (defensive, ne raise)."""
    from evals.framework import budget

    assert budget.count_calls_last_5h(tmp_path / "nonexistent", now=1000.0) == 0


def test_count_includes_recent_calls(tmp_path: Path) -> None:
    """Pozivi unutar 5h prozora se broje."""
    from evals.framework import budget

    now = 100000.0
    budget.record_call(tmp_path, timestamp=now - 100)  # 100s prije
    budget.record_call(tmp_path, timestamp=now - 3600)  # 1h prije
    budget.record_call(tmp_path, timestamp=now - 5 * 3600 + 60)  # 4h59m prije
    assert budget.count_calls_last_5h(tmp_path, now=now) == 3


def test_count_excludes_old_calls(tmp_path: Path) -> None:
    """Pozivi stariji od 5h se NE broje (sliding window)."""
    from evals.framework import budget

    now = 100000.0
    budget.record_call(tmp_path, timestamp=now - 5 * 3600 - 60)  # 5h1m prije
    budget.record_call(tmp_path, timestamp=now - 6 * 3600)  # 6h prije
    budget.record_call(tmp_path, timestamp=now - 100)  # recent (treba da se broji)
    assert budget.count_calls_last_5h(tmp_path, now=now) == 1


def test_count_handles_corrupted_log_lines(tmp_path: Path) -> None:
    """Corrupted JSON redovi se skipuju, ne raise."""
    from evals.framework import budget

    log = tmp_path / "pwr_calls.jsonl"
    log.write_text(
        '{"ts": 1000.0}\n{not valid json\n{"ts": 2000.0}\n',
        encoding="utf-8",
    )
    assert budget.count_calls_last_5h(tmp_path, now=3000.0) == 2


# --------------------------- should_pause ---------------------------


def test_should_pause_false_below_threshold(tmp_path: Path) -> None:
    """count < max_calls * threshold → False."""
    from evals.framework import budget

    now = 100000.0
    # 5 calls, max_calls=80, threshold=0.65 → pause na 52; 5 < 52 → False.
    for _ in range(5):
        budget.record_call(tmp_path, timestamp=now - 10)
    assert budget.should_pause(tmp_path, now=now, max_calls=80, threshold=0.65) is False


def test_should_pause_true_at_threshold(tmp_path: Path) -> None:
    """count == max_calls * threshold → True (uključujući granicu)."""
    from evals.framework import budget

    now = 100000.0
    # 52 calls = 80 * 0.65 → True.
    for _ in range(52):
        budget.record_call(tmp_path, timestamp=now - 10)
    assert budget.should_pause(tmp_path, now=now, max_calls=80, threshold=0.65) is True


def test_should_pause_true_above_threshold(tmp_path: Path) -> None:
    """count > threshold → True."""
    from evals.framework import budget

    now = 100000.0
    for _ in range(70):
        budget.record_call(tmp_path, timestamp=now - 10)
    assert budget.should_pause(tmp_path, now=now, max_calls=80, threshold=0.65) is True


def test_should_pause_defaults(tmp_path: Path) -> None:
    """Default max_calls=80, threshold=0.65 (dogovoreno sa korisnikom 2026-05-24)."""
    from evals.framework import budget

    assert budget.DEFAULT_MAX_CALLS == 80
    assert budget.DEFAULT_THRESHOLD == 0.65


def test_list_calls_in_window_empty_log(tmp_path: Path) -> None:
    """list_calls_in_window vraća [] ako log ne postoji."""
    from evals.framework import budget

    assert budget.list_calls_in_window(tmp_path / "no_log", now=1000.0) == []


def test_list_calls_in_window_filters_out_of_window_and_sorts(tmp_path: Path) -> None:
    """Vraća SAMO ts u 5h prozoru, sortirano rastuće (Bug #1 fix kontrakt)."""
    from evals.framework import budget

    now = 100000.0
    # 3 stare (van prozora) + 4 svježe (u prozoru, ubačene neredom).
    budget.record_call(tmp_path, timestamp=now - 6 * 3600)
    budget.record_call(tmp_path, timestamp=now - 10 * 3600)
    budget.record_call(tmp_path, timestamp=now - 7 * 3600)
    budget.record_call(tmp_path, timestamp=now - 100)
    budget.record_call(tmp_path, timestamp=now - 3000)
    budget.record_call(tmp_path, timestamp=now - 500)
    budget.record_call(tmp_path, timestamp=now - 1500)

    result = budget.list_calls_in_window(tmp_path, now=now)
    assert result == [now - 3000, now - 1500, now - 500, now - 100]


def test_list_calls_in_window_skips_corrupted(tmp_path: Path) -> None:
    """Corrupted JSON redovi se skipuju (defensive)."""
    from evals.framework import budget

    log = tmp_path / "pwr_calls.jsonl"
    log.write_text(
        '{"ts": 1000}\n{not valid json\n{"ts": 2000}\n',
        encoding="utf-8",
    )
    result = budget.list_calls_in_window(tmp_path, now=3000.0)
    assert result == [1000.0, 2000.0]


def test_should_pause_respects_sliding_window(tmp_path: Path) -> None:
    """Stari pozivi (> 5h) ne broje se u should_pause."""
    from evals.framework import budget

    now = 100000.0
    # 60 starih (> 5h) + 10 novih → ukupno 10 u prozoru, pause = False.
    for _ in range(60):
        budget.record_call(tmp_path, timestamp=now - 6 * 3600)
    for _ in range(10):
        budget.record_call(tmp_path, timestamp=now - 100)
    assert budget.should_pause(tmp_path, now=now, max_calls=80, threshold=0.65) is False
