"""Integration test za ralph/status.sh bash skript.

Pokreće skript kao subprocess i verifikuje exit code + ključne sekcije
u output-u. Ne validira konkretne vrijednosti (commits/log-ovi se mijenjaju)
— samo strukturu.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_status_script() -> subprocess.CompletedProcess:
    """Helper: pokreni ralph/status.sh iz project root-a."""
    return subprocess.run(
        ["bash", "ralph/status.sh"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_status_script_exits_zero() -> None:
    """Skript ne crash-uje (exit 0) bez obzira na Ralph status."""
    result = _run_status_script()
    assert result.returncode == 0, f"status.sh exit {result.returncode}\nstderr:\n{result.stderr}"


def test_status_script_shows_required_sections() -> None:
    """Output sadrži sve glavne sekcije dashboard-a (regression guard)."""
    result = _run_status_script()
    assert "Ralph status" in result.stdout
    assert "-- proces --" in result.stdout
    assert "-- posljednji log" in result.stdout
    assert "-- posljednja 3 commit-a" in result.stdout
    assert "-- IMPLEMENTATION_PLAN.md --" in result.stdout
    assert "-- posljednji eval" in result.stdout


def test_status_script_detects_ralph_not_running() -> None:
    """Kad nijedan ralph proces ne radi, skript jasno signalizira NE RADI.

    Skip ako je Ralph trenutno aktivan (npr. test pokrenut iz Ralph petlje
    kao backpressure step) — tada status.sh legitimno javlja RADI, što ne
    konflikt-uje sa ovom branom testa.
    """
    ralph_active = (
        subprocess.run(["pgrep", "-f", "ralph/ralph.sh"], capture_output=True, text=True).returncode
        == 0
    )
    if ralph_active:
        pytest.skip("Ralph aktivan — NE RADI grana se ne može provjeriti")
    result = _run_status_script()
    assert "NE RADI" in result.stdout


def test_status_script_reads_plan_now_top_task() -> None:
    """Skript citira top Now task iz IMPLEMENTATION_PLAN.md."""
    plan_path = PROJECT_ROOT / "ralph" / "IMPLEMENTATION_PLAN.md"
    if not plan_path.exists():
        pytest.skip("IMPLEMENTATION_PLAN.md ne postoji u ovom branchu")

    result = _run_status_script()
    # Mora biti sekcija "Top Now task:" praćena nekim sadržajem.
    assert "Top Now task" in result.stdout
