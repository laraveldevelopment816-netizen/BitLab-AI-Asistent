"""Unit testovi za Ralph prompt strukturu — guardrails kao testovi.

Provjerava da ralph/PROMPT_build.md i ralph/AGENTS.md drže ključne sekcije
i instrukcije koje Ralph mora poštovati. Regression guard — kasniji edit
ne smije slučajno obrisati guardrail.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_BUILD = PROJECT_ROOT / "ralph" / "PROMPT_build.md"
AGENTS_MD = PROJECT_ROOT / "ralph" / "AGENTS.md"


def test_prompt_build_md_exists() -> None:
    assert PROMPT_BUILD.exists(), "ralph/PROMPT_build.md mora postojati"


def test_prompt_has_status_block_instruction() -> None:
    """Faza 7 mora tražiti STATUS blok ispis."""
    content = PROMPT_BUILD.read_text(encoding="utf-8")
    assert "STATUS blok" in content
    # Konkretan format reda mora biti dokumentovan.
    assert "STATUS | iter=" in content


def test_prompt_has_llm_backend_guardrail() -> None:
    """Guardrail 999.9 (PWR-first dispatch) mora biti tu."""
    content = PROMPT_BUILD.read_text(encoding="utf-8")
    assert "999.9" in content
    assert "run_agent" in content
    assert "Anthropic" in content


def test_prompt_disallows_new_feature_branch() -> None:
    """Faza 5 mora reći 'NE pravi novu granu' (jedna grana za eksperiment)."""
    content = PROMPT_BUILD.read_text(encoding="utf-8")
    assert "NE pravi novu granu" in content
    # Mora pominjati zadržavanje na istoj/trenutnoj grani (formulacija fleksibilna).
    assert (
        "Ostani na grani" in content
        or "istu feature granu" in content
        or "trenutnoj feature grani" in content
    )


def test_agents_md_exists() -> None:
    assert AGENTS_MD.exists(), "ralph/AGENTS.md mora postojati"


def test_agents_md_has_sample_first_rule() -> None:
    """Pravilo 6 (sample-first) mora biti u AGENTS.md."""
    content = AGENTS_MD.read_text(encoding="utf-8")
    assert "--mode sample" in content
    assert "fail-pattern" in content.lower() or "fail pattern" in content.lower()


def test_agents_md_documents_status_sh() -> None:
    """status.sh komanda mora biti u command tabeli."""
    content = AGENTS_MD.read_text(encoding="utf-8")
    assert "status.sh" in content
