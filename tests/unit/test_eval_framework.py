"""Unit testovi za eval framework: judge, loader, reporter čiste funkcije."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.framework import judge, loader, reporter
from evals.framework.types import EvalEntry, EvalVerdict

pytestmark = pytest.mark.unit


# --------------------------- judge.verdict_routing ---------------------------


def _entry(**overrides) -> EvalEntry:
    base: dict = {
        "id": "e",
        "query": "q",
        "history": [],
        "expect": {},
        "tags": [],
    }
    base.update(overrides)
    return base  # type: ignore[return-value]


def test_routing_pass_when_tool_matches() -> None:
    entry = _entry(expect={"tool": "category_overview", "args_subset": {"category_id": 151}})
    calls = [{"name": "category_overview", "args": {"category_id": 151}}]
    assert judge.verdict_routing(entry, calls) == "PASS"


def test_routing_fail_when_wrong_tool() -> None:
    entry = _entry(expect={"tool": "category_overview", "args_subset": {}})
    calls = [{"name": "search_products", "args": {}}]
    assert judge.verdict_routing(entry, calls) == "FAIL"


def test_routing_fail_when_no_tool_called_but_expected() -> None:
    entry = _entry(expect={"tool": "category_overview"})
    assert judge.verdict_routing(entry, []) == "FAIL"


def test_routing_pass_when_negative_entry_no_tool() -> None:
    entry = _entry(expect={"tool": None})
    assert judge.verdict_routing(entry, []) == "PASS"


def test_routing_fail_when_negative_entry_tool_called() -> None:
    entry = _entry(expect={"tool": None})
    calls = [{"name": "search_products", "args": {}}]
    assert judge.verdict_routing(entry, calls) == "FAIL"


def test_routing_na_when_no_tool_in_expect() -> None:
    entry = _entry(expect={"args_query_contains": "skener"})
    assert judge.verdict_routing(entry, []) == "NA"


def test_routing_args_subset_ignores_extra_actual_args() -> None:
    entry = _entry(expect={"tool": "search_products", "args_subset": {"category_id": 175}})
    calls = [{"name": "search_products", "args": {"category_id": 175, "extra": "ok"}}]
    assert judge.verdict_routing(entry, calls) == "PASS"


def test_routing_fail_when_args_subset_value_mismatch() -> None:
    entry = _entry(expect={"tool": "search_products", "args_subset": {"category_id": 175}})
    calls = [{"name": "search_products", "args": {"category_id": 999}}]
    assert judge.verdict_routing(entry, calls) == "FAIL"


# --------------------------- judge.verdict_result ---------------------------


def test_result_na_when_no_result_clause() -> None:
    entry = _entry(expect={"tool": "search_products"})
    assert judge.verdict_result(entry, [], "") == "NA"


def test_result_pass_when_args_query_contains_matches() -> None:
    entry = _entry(expect={"args_query_contains": "skener"})
    calls = [{"name": "search_products", "args": {"query": "laserski skener"}}]
    assert judge.verdict_result(entry, calls, "") == "PASS"


def test_result_fail_when_args_query_contains_missing() -> None:
    entry = _entry(expect={"args_query_contains": "skener"})
    calls = [{"name": "search_products", "args": {"query": "neki drugi"}}]
    assert judge.verdict_result(entry, calls, "") == "FAIL"


def test_result_warn_when_rag_metrics_not_yet_supported() -> None:
    entry = _entry(expect={"min_results": 3})
    assert judge.verdict_result(entry, [], "") == "WARN"


# --------------------------- judge.verdict_overall ---------------------------


def test_overall_pass_when_both_pass() -> None:
    assert judge.verdict_overall("PASS", "PASS") == "PASS"


def test_overall_pass_when_routing_pass_result_na() -> None:
    assert judge.verdict_overall("PASS", "NA") == "PASS"


def test_overall_fail_when_any_fail() -> None:
    assert judge.verdict_overall("FAIL", "PASS") == "FAIL"
    assert judge.verdict_overall("PASS", "FAIL") == "FAIL"


def test_overall_warn_when_warn_no_fail() -> None:
    assert judge.verdict_overall("PASS", "WARN") == "WARN"
    assert judge.verdict_overall("WARN", "NA") == "WARN"


def test_overall_na_when_both_na() -> None:
    assert judge.verdict_overall("NA", "NA") == "NA"


# --------------------------- loader ---------------------------


def test_loader_parses_basic_jsonl(tmp_path: Path) -> None:
    suite = tmp_path / "test.jsonl"
    suite.write_text(
        '{"id":"a","query":"hi","expect":{"tool":"search"}}\n'
        '{"id":"b","query":"bye","expect":{"tool":null}}\n',
        encoding="utf-8",
    )
    entries = loader.load_suite(suite)
    assert len(entries) == 2
    assert entries[0]["id"] == "a"
    assert entries[1]["expect"]["tool"] is None


def test_loader_skips_blank_and_comment_lines(tmp_path: Path) -> None:
    suite = tmp_path / "test.jsonl"
    suite.write_text(
        '\n// komentar\n{"id":"a","query":"x","expect":{}}\n\n',
        encoding="utf-8",
    )
    entries = loader.load_suite(suite)
    assert len(entries) == 1


def test_loader_defaults_history_and_tags(tmp_path: Path) -> None:
    suite = tmp_path / "test.jsonl"
    suite.write_text('{"id":"a","query":"x","expect":{}}\n', encoding="utf-8")
    entries = loader.load_suite(suite)
    assert entries[0]["history"] == []
    assert entries[0]["tags"] == []


def test_loader_raises_on_missing_id(tmp_path: Path) -> None:
    suite = tmp_path / "test.jsonl"
    suite.write_text('{"query":"x","expect":{}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="nedostaje 'id'"):
        loader.load_suite(suite)


def test_loader_raises_on_invalid_json(tmp_path: Path) -> None:
    suite = tmp_path / "test.jsonl"
    suite.write_text("{not valid json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON parse error"):
        loader.load_suite(suite)


# --------------------------- reporter ---------------------------


def _make_verdict(entry_id: str, overall: str = "PASS") -> EvalVerdict:
    return {
        "entry_id": entry_id,
        "routing": "PASS",
        "result": "NA",
        "overall": overall,  # type: ignore[typeddict-item]
        "actual_tool_calls": [],
        "reply": "",
        "iterations": 1,
        "error": None,
        "elapsed_ms": 100,
    }


def test_reporter_writes_jsonl(tmp_path: Path) -> None:
    verdicts = [_make_verdict("a"), _make_verdict("b")]
    out = reporter.write_jsonl(tmp_path, "test", "label", verdicts)
    assert out.exists()
    lines = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["entry_id"] == "a"


def test_reporter_writes_html_with_summary(tmp_path: Path) -> None:
    verdicts = [_make_verdict("a", "PASS"), _make_verdict("b", "FAIL")]
    out = reporter.write_html(tmp_path, "test", "label", verdicts)
    html = out.read_text(encoding="utf-8")
    assert "PASS: 1" in html
    assert "FAIL: 1" in html
    assert "Pass rate: 50.0%" in html


def test_reporter_empty_verdicts_zero_pass_rate(tmp_path: Path) -> None:
    out = reporter.write_html(tmp_path, "test", "label", [])
    html = out.read_text(encoding="utf-8")
    assert "Pass rate: 0.0%" in html
