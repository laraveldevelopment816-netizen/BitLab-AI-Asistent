"""Integration testovi: runner piše ralph/PAUSE marker na exit 3.

TDD RED — runner trenutno samo snima checkpoint i exit-uje 3. GREEN dodaje
write PAUSE marker (sa until=<epoch> reset procjenom) tako da ralph.sh
između iteracija detektuje PAUSE i pauzira poll petlju.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.framework import runner

pytestmark = pytest.mark.integration


def _write_suite(tmp_path: Path, entries: list[str]) -> Path:
    suite = tmp_path / "test_suite.jsonl"
    suite.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return suite


def _suite_with_n_entries(tmp_path: Path, n: int) -> Path:
    return _write_suite(
        tmp_path,
        [
            f'{{"id":"e{i}","query":"x","expect":{{"tool":"category_overview","args_subset":{{"category_id":17}}}}}}'
            for i in range(n)
        ],
    )


def _ok_response() -> dict:
    return {
        "reply": "ok",
        "tool_calls": [{"name": "category_overview", "args": {"category_id": 17}}],
        "iterations": 1,
    }


@pytest.fixture
def stable_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "evals.framework.runner._get_signature",
        lambda: ("test-prompt", "test-tools"),
    )


def test_runner_writes_pause_marker_on_budget_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Budget pause → pored checkpoint-a, snima `pause_file` sa until=<epoch>."""
    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())
    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: True)
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: None)
    monkeypatch.setattr("evals.framework.budget.count_calls_last_5h", lambda *a, **k: 60)

    suite = _suite_with_n_entries(tmp_path, 3)
    pause_file = tmp_path / "PAUSE"

    exit_code = runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="bg",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
        pause_file=pause_file,
        budget_dir=tmp_path / "budget",
    )
    assert exit_code == 3
    assert pause_file.exists(), "pause_file mora biti napisan pri pauzi"
    content = pause_file.read_text(encoding="utf-8")
    assert "until=" in content, f"PAUSE mora imati until=<epoch>, dobio: {content}"


def test_runner_writes_pause_marker_on_rate_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Rate limit pause (exception) → isto piše pause_file."""
    from evals.framework.errors import RateLimitDetected

    call_count = {"n": 0}

    def maybe_rate_limit(*a, **k):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise RateLimitDetected("PWR session limit")
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", maybe_rate_limit)
    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: False)
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: None)

    suite = _suite_with_n_entries(tmp_path, 5)
    pause_file = tmp_path / "PAUSE"

    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="rl",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
        pause_file=pause_file,
        budget_dir=tmp_path / "budget",
    )
    assert pause_file.exists()
    assert "until=" in pause_file.read_text(encoding="utf-8")


def test_runner_pause_marker_until_is_valid_epoch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """until=<epoch> mora biti integer broj sekundi, parsable."""
    import time

    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())
    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: True)
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: None)
    monkeypatch.setattr("evals.framework.budget.count_calls_last_5h", lambda *a, **k: 60)

    suite = _suite_with_n_entries(tmp_path, 1)
    pause_file = tmp_path / "PAUSE"

    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="bg",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
        pause_file=pause_file,
        budget_dir=tmp_path / "budget",
    )
    content = pause_file.read_text(encoding="utf-8")
    # Izvuci until vrijednost — mora biti broj, mora biti u razumnoj budućnosti.
    until_line = next(line for line in content.split("\n") if line.startswith("until="))
    until_value = float(until_line[len("until=") :].strip())
    now = time.time()
    assert until_value > now - 60, "until mora biti u budućnosti (ili max ~1min u prošlosti)"
    assert until_value < now + 7 * 3600, "until ne smije biti više od 7h u budućnosti"


def test_estimate_reset_uses_window_oldest_not_global_oldest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug #1 fix: _estimate_reset_epoch ignoriše ts-e van 5h prozora.

    Scenario: log akumulira ts-e iz starije sesije (>5h staro) + svježe. Stara
    implementacija je vraćala `min(global) + 5h` = past epoch → PAUSE marker
    odmah expired → infinite loop. Fix mora vratiti ts U PROZORU + 5h (budućnost).
    """
    from evals.framework import budget
    from evals.framework.runner import _estimate_reset_epoch

    budget_dir = tmp_path / "budget"
    now = 100000.0

    # 5 starih ts (12h staro = van prozora) + 52 svježih (oldest 1h staro).
    for _ in range(5):
        budget.record_call(budget_dir, timestamp=now - 12 * 3600)
    for i in range(52):
        budget.record_call(budget_dir, timestamp=now - 3600 + i)

    result = _estimate_reset_epoch(budget_dir, max_calls=80, now=now)
    # Threshold = 80 * 0.65 = 52. count = 52. target_idx = 0. → oldest in window + 5h.
    expected = int((now - 3600) + budget.WINDOW_SECONDS)
    assert result == expected
    assert result > now, "rezultat MORA biti u budućnosti, ne past epoch (Bug #1)"


def test_estimate_reset_returns_target_ts_for_slot_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kad count > threshold, target je ts pri kojem (count - threshold + 1) najstarijih ispadne."""
    from evals.framework import budget
    from evals.framework.runner import _estimate_reset_epoch

    budget_dir = tmp_path / "budget"
    now = 100000.0

    # 60 ts u prozoru, rastući po 60s intervalu, oldest 4h staro.
    for i in range(60):
        budget.record_call(budget_dir, timestamp=now - 4 * 3600 + i * 60)

    # max_calls=80, threshold=52. count=60, target_idx = 60 - 52 = 8.
    # Kad sorted[8] ispadne (= 9. najstariji), count pada na 51 (< 52). Target = sorted[8] + 5h.
    result = _estimate_reset_epoch(budget_dir, max_calls=80, now=now)
    expected_ts = now - 4 * 3600 + 8 * 60
    expected = int(expected_ts + budget.WINDOW_SECONDS)
    assert result == expected


def test_estimate_reset_empty_window_falls_back_to_now_plus_5h(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sve ts van prozora (samo stara sesija) → now+5h fallback, ne past epoch."""
    from evals.framework import budget
    from evals.framework.runner import _estimate_reset_epoch

    budget_dir = tmp_path / "budget"
    now = 100000.0
    for _ in range(10):
        budget.record_call(budget_dir, timestamp=now - 10 * 3600)

    result = _estimate_reset_epoch(budget_dir, max_calls=80, now=now)
    expected = int(now + budget.WINDOW_SECONDS)
    assert result == expected
    assert result > now


def test_runner_clean_completion_does_not_write_pause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Posle uspješnog run-a, pause_file NIJE kreiran (regression — proaktivna pauza
    samo na rate limit ili budget exhausted)."""
    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())
    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: False)
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: None)

    suite = _suite_with_n_entries(tmp_path, 2)
    pause_file = tmp_path / "PAUSE"

    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="ok",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
        pause_file=pause_file,
        budget_dir=tmp_path / "budget",
    )
    assert not pause_file.exists(), "clean run NE SMIJE pisati pause marker"

    # Verifikuj da inverse — checkpoint i pause oba postoje na pauzi (sanity).
    # (Ne moramo retestirati ovdje, već ide kroz druge testove.)
    _ = json
