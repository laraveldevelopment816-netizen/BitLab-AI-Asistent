"""Integration testovi za eval runner checkpoint + --resume mehanizam.

TDD RED faza — runner.run_suite trenutno nema `resume_label` parametar, nema
checkpoint write-a, nema exit kod 3 za rate-limit. GREEN faza dodaje sve to.

Scenario:
- Rate limit lupi mid-run → snima `<suite>-<label>.checkpoint.json` sa next_index.
- Runner exit-uje sa kodom 3 (specifičan za rate limit).
- Resume pokret čita checkpoint, kreće od next_index, na clean completion
  briše checkpoint.
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


def _ok_response(category_id: int = 17) -> dict:
    return {
        "reply": "ok",
        "tool_calls": [{"name": "category_overview", "args": {"category_id": category_id}}],
        "iterations": 1,
    }


@pytest.fixture
def stable_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force-uje stable signature + disable real budget gate (test izolacija)."""
    monkeypatch.setattr(
        "evals.framework.runner._get_signature",
        lambda: ("test-prompt", "test-tools"),
    )
    # Budget bi čitao pravi ~/.cache/bitlab-ralph log — disable za izolovan test.
    monkeypatch.setattr("evals.framework.budget.should_pause", lambda *a, **k: False)
    monkeypatch.setattr("evals.framework.budget.record_call", lambda *a, **k: None)


def _suite_with_n_entries(tmp_path: Path, n: int) -> Path:
    return _write_suite(
        tmp_path,
        [
            f'{{"id":"e{i}","query":"x","expect":{{"tool":"category_overview","args_subset":{{"category_id":17}}}}}}'
            for i in range(n)
        ],
    )


# --------------------------- exit kod 3 + checkpoint write ---------------------------


def test_runner_returns_exit_code_3_on_rate_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """RateLimitDetected sredinom run-a → runner exit 3 (specifičan signal)."""
    from evals.framework.errors import RateLimitDetected

    call_count = {"n": 0}

    def maybe_rate_limit(*a, **k):
        call_count["n"] += 1
        if call_count["n"] >= 3:
            raise RateLimitDetected("PWR session limit")
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", maybe_rate_limit)

    suite = _suite_with_n_entries(tmp_path, 5)
    exit_code = runner.run_suite(
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
    )
    assert exit_code == 3, f"očekivao exit 3 za rate limit, dobio {exit_code}"


def test_runner_writes_checkpoint_on_rate_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Checkpoint fajl ima next_index = entry koji je rate-limit-ovan."""
    from evals.framework.errors import RateLimitDetected

    call_count = {"n": 0}

    def maybe_rate_limit(*a, **k):
        call_count["n"] += 1
        if call_count["n"] >= 3:
            raise RateLimitDetected("PWR rate limit")
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", maybe_rate_limit)

    suite = _suite_with_n_entries(tmp_path, 5)
    run_dir = tmp_path / "runs"
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="rl",
        limit=None,
        fail_fast=False,
        run_dir=run_dir,
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
    )
    cp_file = run_dir / "test_suite-rl.checkpoint.json"
    assert cp_file.exists(), f"checkpoint fajl mora postojati u {run_dir}"
    cp = json.loads(cp_file.read_text(encoding="utf-8"))
    # Prva 2 entry su prošla (indexes 0, 1); treći (index 2) je rate-limit-ovan.
    # next_index je entry koji se mora ponoviti pri resume-u.
    assert cp["next_index"] == 2
    assert cp["label"] == "rl"


# --------------------------- resume ---------------------------


def test_runner_resume_starts_from_checkpoint_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """resume_label='rl' → čita checkpoint, kreće od next_index, samo (N - next_index) poziva."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    run_dir = tmp_path / "runs"
    run_dir.mkdir(parents=True)
    cp_file = run_dir / "test_suite-rl.checkpoint.json"
    cp_file.write_text(json.dumps({"next_index": 3, "label": "rl"}), encoding="utf-8")

    suite = _suite_with_n_entries(tmp_path, 5)
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="rl",
        limit=None,
        fail_fast=False,
        run_dir=run_dir,
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label="rl",
    )
    # 5 entries u suite, next_index=3 → ostaju 2 nove (indexes 3, 4).
    assert call_count["n"] == 2


def test_runner_resume_missing_checkpoint_starts_from_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """resume_label sa nepostojećim checkpoint-om — kreće normalno od 0 (defensive)."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    suite = _suite_with_n_entries(tmp_path, 3)
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="nonexistent",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label="nonexistent",
    )
    assert call_count["n"] == 3


# --------------------------- cleanup checkpoint ---------------------------


def test_runner_cleans_checkpoint_on_clean_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Posle uspješnog completion-a, checkpoint je obrisan (no stale resume traps)."""
    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())

    suite = _write_suite(
        tmp_path,
        [
            '{"id":"e1","query":"x","expect":{"tool":"category_overview","args_subset":{"category_id":17}}}'
        ],
    )
    run_dir = tmp_path / "runs"
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="ok",
        limit=None,
        fail_fast=False,
        run_dir=run_dir,
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
        resume_label=None,
    )
    cp_file = run_dir / "test_suite-ok.checkpoint.json"
    assert not cp_file.exists(), (
        f"checkpoint NE SMIJE postojati posle clean completion, ali postoji: {cp_file}"
    )
