"""Integration testovi za runner + budget tracker.

TDD RED — runner trenutno ne integriše budget. GREEN dodaje:
- prije svakog `_run_entry` poziva, provjeri `budget.should_pause`;
  ako True → snima checkpoint sa next_index=i, exit kod 3.
- posle uspješnog `_run_entry`, zovi `budget.record_call`.
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


def _ok_response(category_id: int = 17) -> dict:
    return {
        "reply": "ok",
        "tool_calls": [{"name": "category_overview", "args": {"category_id": category_id}}],
        "iterations": 1,
    }


@pytest.fixture
def stable_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "evals.framework.runner._get_signature",
        lambda: ("test-prompt", "test-tools"),
    )


# --------------------------- pause ---------------------------


def test_runner_pauses_when_budget_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Kad `should_pause` vrati True (treći check), runner snima checkpoint i exit 3."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    check_count = {"n": 0}

    def pausing_check(*a, **k):
        check_count["n"] += 1
        # Prvi i drugi check (prije index 0 i 1) → False, treći (prije index 2) → True.
        return check_count["n"] >= 3

    monkeypatch.setattr("evals.framework.budget.should_pause", pausing_check)
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: None)

    suite = _suite_with_n_entries(tmp_path, 5)
    run_dir = tmp_path / "runs"
    exit_code = runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="bg",
        limit=None,
        fail_fast=False,
        run_dir=run_dir,
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
    )
    assert exit_code == 3
    # Pauza prije index 2 → 2 uspješna poziva.
    assert call_count["n"] == 2
    cp = run_dir / "test_suite-bg.checkpoint.json"
    assert cp.exists()
    cp_data = json.loads(cp.read_text())
    assert cp_data["next_index"] == 2
    # Reason mora pomenuti budget (da Ralph ralph.sh dijagnostika može odlučiti pauza tip).
    assert "budget" in cp_data["reason"].lower()


def test_runner_records_call_per_successful_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Posle svakog uspješnog _run_entry, budget.record_call se zvan."""
    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())

    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: False)

    recorded = []

    def recording(*a, **k):
        recorded.append(True)

    monkeypatch.setattr("evals.framework.budget.record_call", recording)

    suite = _suite_with_n_entries(tmp_path, 3)
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="rc",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
    )
    assert len(recorded) == 3


def test_runner_continues_when_budget_not_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Kad should_pause uvijek False, runner radi kompletan suite (regression — default put)."""
    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())
    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: False)
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: None)

    suite = _suite_with_n_entries(tmp_path, 5)
    exit_code = runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="full",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
    )
    assert exit_code == 0


def test_runner_does_not_record_when_cache_hit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cache hit ne pravi HTTP poziv → ne troši budget → ne record_call."""
    from evals.framework import cache

    # Stabilan signature da cache work-uje.
    monkeypatch.setattr(
        "evals.framework.runner._get_signature",
        lambda: ("prompt-stable", "tools-stable"),
    )
    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())
    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: False)

    recorded = []
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: recorded.append(True))

    # Pre-populiraj cache za prvi entry.
    cache_dir = tmp_path / "cache"
    entry_in_cache = {
        "id": "e0",
        "query": "x",
        "history": [],
        "expect": {"tool": "category_overview", "args_subset": {"category_id": 17}},
        "tags": [],
    }
    hash_key = cache.compute_hash(entry_in_cache, "prompt-stable", "tools-stable")
    cache.cache_put(
        cache_dir,
        hash_key,
        {
            "entry_id": "e0",
            "routing": "PASS",
            "result": "NA",
            "overall": "PASS",
            "actual_tool_calls": [],
            "reply": "",
            "iterations": 1,
            "error": None,
            "elapsed_ms": 1,
        },
    )

    suite = _suite_with_n_entries(tmp_path, 2)  # e0 (cache hit), e1 (poziv)
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="ch",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=cache_dir,
        use_cache=True,
        mode="full",
        resume_label=None,
    )
    # Samo jedan record_call (e1, e0 je cache hit).
    assert len(recorded) == 1
