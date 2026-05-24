"""Integration testovi za eval runner — run_suite end-to-end sa cache + sample mode.

Mock-uje `evals.framework.client.call_chat` da ne ide na HTTP. Test
verifikuje da runner ispravno integriše cache lookup/put, sample mode
selekciju, fail-fast, i limit argument.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.framework import runner

pytestmark = pytest.mark.integration


def _write_suite(tmp_path: Path, entries: list[str]) -> Path:
    """Helper: napiše JSONL eval set u tmp_path."""
    suite = tmp_path / "test_suite.jsonl"
    suite.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return suite


def _ok_response(category_id: int = 17) -> dict:
    """Mock response sa jednim tool call-om koji odgovara expect-u."""
    return {
        "reply": "ok",
        "tool_calls": [{"name": "category_overview", "args": {"category_id": category_id}}],
        "iterations": 1,
    }


def _fail_response() -> dict:
    """Mock response bez tool call-a (ovo će routing PASS samo ako expect.tool=None)."""
    return {"reply": "fallback", "tool_calls": [], "iterations": 1}


@pytest.fixture
def stable_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force-uje deterministički cache signature, nezavisno od stvarnog app/ modula."""
    monkeypatch.setattr(
        "evals.framework.runner._get_signature",
        lambda: ("test-prompt-v1", "test-tools-sig-v1"),
    )


# --------------------------- output fajlovi ---------------------------


def test_run_suite_writes_jsonl_and_html(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Posle uspješnog run-a, JSONL i HTML postoje u run_dir."""
    monkeypatch.setattr("evals.framework.client.call_chat", lambda *a, **k: _ok_response())

    suite = _write_suite(
        tmp_path,
        [
            '{"id":"e1","query":"x","expect":{"tool":"category_overview","args_subset":{"category_id":17}}}'
        ],
    )
    cache_dir = tmp_path / "cache"
    run_dir = tmp_path / "runs"

    exit_code = runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="test",
        limit=None,
        fail_fast=False,
        run_dir=run_dir,
        cache_dir=cache_dir,
        use_cache=True,
        mode="full",
    )
    assert exit_code == 0
    jsonl_files = list(run_dir.glob("*.jsonl"))
    html_files = list(run_dir.glob("*.html"))
    assert len(jsonl_files) == 1
    assert len(html_files) == 1


# --------------------------- limit ---------------------------


def test_run_suite_respects_limit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """--limit 0 ne pravi nijedan HTTP poziv (dry run)."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    suite = _write_suite(
        tmp_path,
        ['{"id":"e1","query":"x","expect":{"tool":"category_overview"}}'] * 3,
    )
    suite_lines = suite.read_text().strip().split("\n")
    # Lines must have unique IDs:
    suite.write_text(
        "\n".join(line.replace('"e1"', f'"e{i}"') for i, line in enumerate(suite_lines)) + "\n"
    )

    exit_code = runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="dry",
        limit=0,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=True,
        mode="full",
    )
    assert exit_code == 0
    assert call_count["n"] == 0


def test_run_suite_respects_positive_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """--limit N obraduje samo prvih N entry-ja."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    suite = _write_suite(
        tmp_path,
        [f'{{"id":"e{i}","query":"x","expect":{{"tool":"category_overview"}}}}' for i in range(5)],
    )

    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="lim",
        limit=2,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=True,
        mode="full",
    )
    assert call_count["n"] == 2


# --------------------------- cache integration ---------------------------


def test_run_suite_cache_hit_skips_http_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """Drugi run sa istim signature-om → cache hit, 0 novih HTTP poziva."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    suite = _write_suite(
        tmp_path,
        [
            '{"id":"e1","query":"x","expect":{"tool":"category_overview","args_subset":{"category_id":17}}}',
            '{"id":"e2","query":"y","expect":{"tool":"category_overview","args_subset":{"category_id":17}}}',
        ],
    )
    cache_dir = tmp_path / "cache"
    run_dir = tmp_path / "runs"

    # Prvi run — cache miss, 2 poziva.
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="r1",
        limit=None,
        fail_fast=False,
        run_dir=run_dir,
        cache_dir=cache_dir,
        use_cache=True,
        mode="full",
    )
    assert call_count["n"] == 2
    assert len(list(cache_dir.glob("*.json"))) == 2

    # Drugi run — cache hit, broj poziva ostaje 2.
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="r2",
        limit=None,
        fail_fast=False,
        run_dir=run_dir,
        cache_dir=cache_dir,
        use_cache=True,
        mode="full",
    )
    assert call_count["n"] == 2


def test_run_suite_no_cache_flag_disables_caching(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """use_cache=False — drugi run i dalje pravi HTTP pozive."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    suite = _write_suite(
        tmp_path,
        [
            '{"id":"e1","query":"x","expect":{"tool":"category_overview","args_subset":{"category_id":17}}}'
        ],
    )
    cache_dir = tmp_path / "cache"

    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="r1",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=cache_dir,
        use_cache=False,
        mode="full",
    )
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="r2",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=cache_dir,
        use_cache=False,
        mode="full",
    )
    assert call_count["n"] == 2
    # Cache dir prazan kad je no-cache.
    assert not cache_dir.exists() or not list(cache_dir.glob("*.json"))


def test_run_suite_cache_invalidates_on_signature_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Promjena signature-a → cache hash drugačiji → novi HTTP poziv."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    suite = _write_suite(
        tmp_path,
        [
            '{"id":"e1","query":"x","expect":{"tool":"category_overview","args_subset":{"category_id":17}}}'
        ],
    )
    cache_dir = tmp_path / "cache"

    # Run sa signature v1.
    monkeypatch.setattr("evals.framework.runner._get_signature", lambda: ("prompt-v1", "tools-v1"))
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="r1",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=cache_dir,
        use_cache=True,
        mode="full",
    )
    assert call_count["n"] == 1

    # Run sa promijenjenom signature v2 → cache miss, novi poziv.
    monkeypatch.setattr("evals.framework.runner._get_signature", lambda: ("prompt-v2", "tools-v1"))
    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="r2",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=cache_dir,
        use_cache=True,
        mode="full",
    )
    assert call_count["n"] == 2


# --------------------------- sample mode ---------------------------


def test_run_suite_sample_mode_picks_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """--mode sample uzima ~30 stratificiranih entry-ja iz veće suite-e."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        return _ok_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    # 50 leaf + 50 parent — bez manual (sve sample mora doći iz auto-gen).
    entries = []
    for i in range(50):
        entries.append(
            f'{{"id":"leaf{i}","query":"q","expect":{{"tool":"category_overview"}},"tags":["auto-gen","leaf"]}}'
        )
        entries.append(
            f'{{"id":"parent{i}","query":"q","expect":{{"tool":"category_overview"}},"tags":["auto-gen","parent"]}}'
        )
    suite = _write_suite(tmp_path, entries)

    runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="samp",
        limit=None,
        fail_fast=False,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="sample",
    )
    # Sample target = 30 → 30 poziva.
    assert call_count["n"] == 30


# --------------------------- fail-fast ---------------------------


def test_run_suite_fail_fast_stops_on_first_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stable_signature: None
) -> None:
    """fail_fast=True — runner staje nakon prvog FAIL-a, ne obraduje ostale."""
    call_count = {"n": 0}

    def counting_call(*a, **k):
        call_count["n"] += 1
        # Vrati ništa (no tool calls) — routing FAIL jer entry očekuje tool.
        return _fail_response()

    monkeypatch.setattr("evals.framework.client.call_chat", counting_call)

    suite = _write_suite(
        tmp_path,
        [f'{{"id":"e{i}","query":"x","expect":{{"tool":"category_overview"}}}}' for i in range(5)],
    )

    exit_code = runner.run_suite(
        suite_path=suite,
        base_url="http://mock",
        label="ff",
        limit=None,
        fail_fast=True,
        run_dir=tmp_path / "runs",
        cache_dir=tmp_path / "cache",
        use_cache=False,
        mode="full",
    )
    assert exit_code == 1  # bar jedan FAIL
    assert call_count["n"] == 1  # stopovan nakon prvog FAIL-a
