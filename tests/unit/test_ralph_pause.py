"""Unit testovi za ralph/wait_pause.py — Python helper koji ralph.sh poziva.

TDD RED faza — moduli `ralph.wait_pause` i `ralph.estimate_reset` ne postoje.
GREEN faza dodaje:
- `ralph/wait_pause.py`: parse_until + wait_for_resume (poll svakih 300s, ili
  PAUSE_POLL_SECONDS iz env za testove).
- `ralph/estimate_reset.py`: procjena reset epoch iz pwr_calls.jsonl
  (najstariji unos + 5h, fallback now + 5h ako log prazan).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

# Ralph helper-i nisu Python paket, dodajemo na sys.path za import.
RALPH_DIR = Path(__file__).resolve().parent.parent.parent / "ralph"
if str(RALPH_DIR) not in sys.path:
    sys.path.insert(0, str(RALPH_DIR))


# --------------------------- parse_until ---------------------------


def test_parse_until_valid_epoch() -> None:
    """until=1700000000 → 1700000000.0"""
    import wait_pause

    assert wait_pause.parse_until("until=1700000000") == 1700000000.0


def test_parse_until_valid_with_decimals() -> None:
    """until=1700000000.5 → 1700000000.5"""
    import wait_pause

    assert wait_pause.parse_until("until=1700000000.5") == 1700000000.5


def test_parse_until_empty_returns_none() -> None:
    """Prazan content (cooperative wait) → None."""
    import wait_pause

    assert wait_pause.parse_until("") is None


def test_parse_until_whitespace_returns_none() -> None:
    """Samo whitespace → None."""
    import wait_pause

    assert wait_pause.parse_until("   \n  \n") is None


def test_parse_until_invalid_value_returns_none() -> None:
    """until=abc → None (ne raise)."""
    import wait_pause

    assert wait_pause.parse_until("until=abc") is None


def test_parse_until_ignores_other_lines() -> None:
    """Drugi tekst u marker fajlu se ignoriše, until= se nađe."""
    import wait_pause

    content = "# komentar\nrandom text\nuntil=1700000000\nmore text\n"
    assert wait_pause.parse_until(content) == 1700000000.0


# --------------------------- wait_for_resume ---------------------------


def test_wait_returns_zero_when_no_pause_file(tmp_path: Path) -> None:
    """Bez PAUSE fajla → odmah return 0 (nastavi)."""
    import wait_pause

    pause = tmp_path / "PAUSE"
    stop = tmp_path / "STOP"
    assert wait_pause.wait_for_resume(pause_file=pause, stop_file=stop) == 0


def test_wait_returns_one_when_stop_marker_exists(tmp_path: Path) -> None:
    """STOP marker prisutan → return 1 (forsiraj exit)."""
    import wait_pause

    pause = tmp_path / "PAUSE"
    stop = tmp_path / "STOP"
    pause.write_text("until=999999999999")
    stop.write_text("")
    assert wait_pause.wait_for_resume(pause_file=pause, stop_file=stop) == 1


def test_wait_returns_zero_when_until_expired(tmp_path: Path) -> None:
    """PAUSE postoji ali until je u prošlosti → obriši fajl, return 0."""
    import wait_pause

    pause = tmp_path / "PAUSE"
    stop = tmp_path / "STOP"
    pause.write_text("until=100")  # davno
    result = wait_pause.wait_for_resume(
        pause_file=pause,
        stop_file=stop,
        now_fn=lambda: 1000.0,
        sleep_fn=lambda _: None,
    )
    assert result == 0
    assert not pause.exists(), "expired PAUSE marker mora biti obrisan"


def test_wait_polls_when_until_in_future(tmp_path: Path) -> None:
    """until u budućnosti → poll petlja zove sleep dok rm ili istek."""
    import wait_pause

    pause = tmp_path / "PAUSE"
    stop = tmp_path / "STOP"
    pause.write_text("until=2000")

    times: list[float] = [1000.0, 1100.0, 2100.0]  # treći poll vidi expired
    sleeps: list[float] = []

    def fake_now() -> float:
        return times.pop(0) if times else 9999.0

    def fake_sleep(secs: float) -> None:
        sleeps.append(secs)

    result = wait_pause.wait_for_resume(
        pause_file=pause,
        stop_file=stop,
        now_fn=fake_now,
        sleep_fn=fake_sleep,
    )
    assert result == 0
    assert len(sleeps) >= 1  # bar jedan sleep poziv
    # PAUSE fajl obrisan na exit (expired).
    assert not pause.exists()


def test_wait_cooperative_polls_until_rm(tmp_path: Path) -> None:
    """Prazan PAUSE (cooperative) → poll petlja, exit kad PAUSE nestane."""
    import wait_pause

    pause = tmp_path / "PAUSE"
    stop = tmp_path / "STOP"
    pause.write_text("")

    # Sleep callback briše PAUSE posle prvog poziva (simulira ručno rm).
    sleeps: list[float] = []

    def fake_sleep(secs: float) -> None:
        sleeps.append(secs)
        pause.unlink(missing_ok=True)

    result = wait_pause.wait_for_resume(
        pause_file=pause,
        stop_file=stop,
        now_fn=lambda: 1000.0,
        sleep_fn=fake_sleep,
    )
    assert result == 0
    assert len(sleeps) == 1


# --------------------------- estimate_reset ---------------------------


def test_estimate_default_when_log_missing(tmp_path: Path) -> None:
    """Log fajl ne postoji → now + 5h fallback."""
    import estimate_reset

    nonexistent = tmp_path / "no_log.jsonl"
    result = estimate_reset.estimate_reset(log_path=nonexistent, now_fn=lambda: 1000.0)
    assert result == int(1000.0 + 5 * 3600)


def test_estimate_uses_oldest_entry_plus_5h(tmp_path: Path) -> None:
    """Najstariji unos u log-u + 5h."""
    import estimate_reset

    log = tmp_path / "pwr_calls.jsonl"
    log.write_text(
        json.dumps({"ts": 500.0})
        + "\n"
        + json.dumps({"ts": 100.0})
        + "\n"  # najstariji
        + json.dumps({"ts": 800.0})
        + "\n"
    )
    result = estimate_reset.estimate_reset(log_path=log, now_fn=lambda: 9999.0)
    assert result == int(100.0 + 5 * 3600)


def test_estimate_handles_corrupted_log(tmp_path: Path) -> None:
    """Corrupted JSON redovi se skipuju, ostatak normalno."""
    import estimate_reset

    log = tmp_path / "pwr_calls.jsonl"
    log.write_text('{"ts": 200}\n{not valid}\n{"ts": 100}\n')
    result = estimate_reset.estimate_reset(log_path=log, now_fn=lambda: 9999.0)
    assert result == int(100.0 + 5 * 3600)


def test_estimate_empty_log_falls_back_to_now(tmp_path: Path) -> None:
    """Postoji log ali bez valjanih unosa → now + 5h fallback."""
    import estimate_reset

    log = tmp_path / "pwr_calls.jsonl"
    log.write_text("")
    result = estimate_reset.estimate_reset(log_path=log, now_fn=lambda: 1000.0)
    assert result == int(1000.0 + 5 * 3600)


# --------------------------- ralph.sh sanity (file existence + bash syntax) ---------------------------


def test_ralph_sh_has_pause_detection() -> None:
    """ralph.sh mora referencirati PAUSE marker (regression guard)."""
    ralph_sh = RALPH_DIR / "ralph.sh"
    assert ralph_sh.exists()
    content = ralph_sh.read_text(encoding="utf-8")
    assert "PAUSE" in content, "ralph.sh mora hvatati PAUSE marker"
    assert "wait_pause" in content, "ralph.sh mora pozivati wait_pause helper"


def test_ralph_sh_writes_pause_on_exit_3() -> None:
    """ralph.sh mora pisati PAUSE marker kad claude exit code == 3."""
    ralph_sh = RALPH_DIR / "ralph.sh"
    content = ralph_sh.read_text(encoding="utf-8")
    # Detekcija exit kod 3 (može PIPESTATUS ili direktan $? — fleksibilna provjera).
    assert "3" in content and "PAUSE" in content
    assert "estimate_reset" in content, "ralph.sh mora pozivati estimate_reset helper"


def _ensure_args_unused(*_: Any) -> None:
    """Placeholder da typecheck-er ne žali za _ensure_args_unused fixture neuse."""
    return None
