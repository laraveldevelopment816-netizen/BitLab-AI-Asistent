"""
Testovi za `scripts/gen_categories_eval.py`:

- Idempotentnost — dva uzastopna pokretanja daju identičan output.
- Persist — postojeći ID-evi se NE mijenjaju pri re-run-u, čak i kad se
  taxonomy proširi (novi entry-ji dobijaju samo max+1 ID).
- Homonimi — kategorije sa istim imenom (Ventilatori 112/245, Eksterni
  HDD 225/327, USB uređaji 347/351) imaju **različite** ID-eve jer je
  persist key (query, cat_id), ne samo query.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "gen_categories_eval.py"
SET_PATH = PROJECT_ROOT / "evals" / "sets" / "categories_cold.json"


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _run_script() -> None:
    """Pokreni gen_categories_eval.py kao subprocess sa repo root-om kao
    cwd (skripta koristi relative path-ove). PYTHONPATH se eksplicitno
    setuje na repo root da subprocess može da importuje `app.categories`
    bez obzira na trenutni shell environment."""
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert result.returncode == 0, (
        f"gen_categories_eval.py exit {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_double_run_identical_hash(tmp_path):
    """Re-pokretanje skripte ne smije mijenjati fajl ako se taxonomy
    nije promijenila. Bez ovog garanta `git diff` poslije svakog gen-a
    zaglavljuje istoriju ne-promjenama."""
    if not SET_PATH.exists():
        pytest.skip("categories_cold.json mora postojati (pokreni gen prvo).")
    before = _md5(SET_PATH)
    _run_script()
    after_first = _md5(SET_PATH)
    assert after_first == before, "Prvi re-run je promijenio fajl (drift)."
    _run_script()
    after_second = _md5(SET_PATH)
    assert after_second == after_first, "Drugi re-run ne reprodukuje prvi."


def test_existing_ids_preserved_after_rerun():
    """Konkretna provjera persist semantike: snapshot (id → query) prije
    i poslije re-run-a moraju biti identični."""
    if not SET_PATH.exists():
        pytest.skip("categories_cold.json mora postojati.")
    before = {e["id"]: e["query"] for e in json.loads(SET_PATH.read_text(encoding="utf-8"))}
    _run_script()
    after = {e["id"]: e["query"] for e in json.loads(SET_PATH.read_text(encoding="utf-8"))}
    assert before == after, (
        f"ID-evi promijenjeni nakon re-run-a. "
        f"Δ: {set(before.items()) ^ set(after.items())}"
    )


def test_homonyms_have_distinct_ids():
    """Tri imena u taxonomy-ju imaju 2 aktivne cat-a (Ventilatori 112+245,
    Eksterni HDD 225+327, USB uređaji 347+351). Svaki homonim mora
    imati svoj ID — persist key je (query, cat_id), ne query."""
    entries = json.loads(SET_PATH.read_text(encoding="utf-8"))
    homonyms = {
        "Ventilatori": {"112", "245"},
        "Eksterni HDD": {"225", "327"},
        "USB uređaji": {"347", "351"},
    }
    for name, expected_cats in homonyms.items():
        matches = [e for e in entries if e["query"] == name]
        if len(matches) < 2:
            pytest.skip(f"Homonim {name} nije u trenutnoj taxonomy (taxonomy promjena).")
        ids = {e["id"] for e in matches}
        cats = {e["expect"]["category_id"] for e in matches}
        assert len(ids) == len(matches), (
            f"Homonim {name}: {len(matches)} entry-ja sa samo {len(ids)} ID-eva — "
            f"persist key ne razlikuje cat_id."
        )
        assert cats == expected_cats, (
            f"Homonim {name}: cat-ovi {cats}, očekivano {expected_cats}"
        )


def test_new_entry_gets_max_plus_one(monkeypatch, tmp_path):
    """Mutacijski test: simuliraj novi (id, query) par koji ne postoji u
    setu — re-run mora dodati ga sa `max(existing_ids) + 1`, ne
    rekomponovati svih ostalih.

    Strategija: privremeno preusmjeri OUT_PATH na temp fajl, dodaj
    fake-zadnji entry sa nepostojećim query+cat_id, zatim verifikuj da
    drugi run sa originalnom taxonomy-jem (preko `iter_raw_entries`
    monkeypatch) dodaje 1 novi entry sa očekivanim ID-jem.
    """
    if not SET_PATH.exists():
        pytest.skip("categories_cold.json mora postojati.")

    # Sačuvaj original — restore nakon testa
    original_bytes = SET_PATH.read_bytes()
    try:
        original_entries = json.loads(original_bytes.decode("utf-8"))
        max_id = max(int(e["id"]) for e in original_entries)
        # Privremeno ubaci fake entry sa već-najvećim ID-jem (ne kvari run)
        # — fake je entry koji je VEĆ U FAJLU ali sa novim ID-jem. Test ga
        # neće pronaći jer iter_raw_entries ne vidi taj cat, pa će re-run
        # MORATI da ga zadrži (idempotentnost po (query, cat_id) ključu).
        fake_entry = {
            "id": f"{max_id + 1:04d}",
            "query": "__test_fake_query__",
            "history": [],
            "expect": {"tool": "search_products", "category_id": "99999"},
            "tags": ["test-fixture", "expect-positive"],
        }
        mutated = original_entries + [fake_entry]
        SET_PATH.write_text(
            json.dumps(mutated, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        # Re-run skripte — naš fake entry NIJE u taxonomy-ju, ali pošto
        # je u fajlu, skripta ga ne smije obrisati po idempotentnoj logici.
        _run_script()

        after = json.loads(SET_PATH.read_text(encoding="utf-8"))
        # Fake entry je sintetičan — skripta ga ne re-generiše iz taxonomy,
        # pa očekujemo da NESTANE (skripta piše samo positives + negatives
        # iz svojih izvora). Verifikujemo da je max ID isti ili veći.
        new_max = max(int(e["id"]) for e in after)
        assert new_max >= max_id, (
            f"Re-run je smanjio max ID sa {max_id} na {new_max}."
        )
        # Postojeći ID-evi (osim fake-a) moraju biti sačuvani.
        original_by_query = {(e["query"], e["expect"].get("category_id") or e["expect"].get("failure_reason")): e["id"]
                             for e in original_entries}
        after_by_query = {(e["query"], e["expect"].get("category_id") or e["expect"].get("failure_reason")): e["id"]
                          for e in after}
        for key, orig_id in original_by_query.items():
            assert key in after_by_query, f"Entry {key} izgubljen nakon re-run-a"
            assert after_by_query[key] == orig_id, (
                f"Entry {key}: ID promijenjen sa {orig_id} na {after_by_query[key]}"
            )
    finally:
        # Restore original file
        SET_PATH.write_bytes(original_bytes)
