"""Ručni smoke za agenta — brzi uvid uživo (NIJE eval).

Pokreće `run_agent` na par reprezentativnih upita i ispisuje šta se desilo:
koji tool je pozvan (+ args), broj iteracija, i tekstualni reply. Za provjeru
ponašanja na oko dok se podešava prompt — bez PASS/FAIL ocjene i bez troška
punog eval-a. Pass-rate se mjeri eval runner-om (`python -m evals.framework.runner`).

Backend je onaj iz `.env` (LLM_BACKEND); po configu je default PWR.

Pokretanje (iz root-a repoa):
    .venv/bin/python scripts/smoke.py                  # default skup upita
    .venv/bin/python scripts/smoke.py "Asus laptopi"   # jedan ad-hoc upit
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Dozvoli `python scripts/smoke.py` iz root-a (stavi repo root na import path).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import run_agent  # noqa: E402

# Reprezentativni upiti — pokrivaju glavne putanje rutiranja.
DEFAULT_QUERIES = [
    "Mobiteli",                  # gola kategorija -> tool (category_overview / search_products)
    "gaming laptop do 1500 KM",  # namjena + cijena -> search_products
    "Asus laptopi",              # brend + leaf -> search_products
    "kakvo je vrijeme danas",    # van kataloga -> bez toola, prirodan reply
]


def smoke(query: str) -> None:
    result = run_agent([{"role": "user", "content": query}])
    tool_calls = result.get("tool_calls", [])
    print(f"\n=== UPIT: {query}")
    print(f"    iteracija : {result.get('iterations')}")
    if tool_calls:
        for tc in tool_calls:
            print(f"    tool      : {tc['name']}  args={json.dumps(tc['args'], ensure_ascii=False)}")
    else:
        print("    tool      : (nijedan pozvan)")
    print(f"    reply     : {result.get('reply', '')!r}")


def main() -> int:
    queries = sys.argv[1:] or DEFAULT_QUERIES
    for q in queries:
        smoke(q)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
