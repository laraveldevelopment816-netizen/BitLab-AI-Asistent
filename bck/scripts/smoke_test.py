#!/usr/bin/env python3
"""
Provjera /api/chat endpointa.
Server mora biti pokrenut: uvicorn app.main:app --reload

Pokretanje:
    python scripts/smoke_test.py
"""
from __future__ import annotations

import sys

import httpx

BASE = "http://localhost:8000"

TESTS = [
    {
        "desc": "Pretraga proizvoda — SSD",
        "payload": {"message": "Imate li SSD 1TB?", "channel": "chat"},
        "expect_tool": "search_products",
    },
    {
        "desc": "FAQ — dostava",
        "payload": {"message": "Kolika je cijena dostave u Banja Luci?", "channel": "chat"},
        "expect_tool": "get_faq",
    },
    {
        "desc": "B2B eskalacija",
        "payload": {
            "message": "Trebam zvaničnu ponudu za 10 laptopa sa JIB-om za firmu.",
            "channel": "chat",
        },
        "expect_tool": "escalate_to_human",
    },
    {
        "desc": "Voice kanal — gaming monitor",
        "payload": {"message": "Imate li gaming monitore do 400 maraka?", "channel": "voice"},
        "expect_tool": "search_products",
    },
]


def main() -> None:
    print(f"BitLab smoke test → {BASE}/api/chat\n{'─' * 50}")

    try:
        httpx.get(f"{BASE}/healthz", timeout=5).raise_for_status()
    except Exception as exc:
        print(f"✗ Server nije dostupan: {exc}")
        print("  Pokreni: uvicorn app.main:app --reload")
        sys.exit(1)

    passed = 0
    for t in TESTS:
        try:
            resp = httpx.post(f"{BASE}/api/chat", json=t["payload"], timeout=60)
            data = resp.json()
        except Exception as exc:
            print(f"✗ [{t['desc']}] — request greška: {exc}\n")
            continue

        tools_used = data.get("tools_used", [])
        ok = resp.status_code == 200 and t["expect_tool"] in tools_used

        if ok:
            passed += 1
            print(f"✓ [{t['desc']}]")
            print(f"  alati: {tools_used}")
            reply_preview = (data.get("reply") or "")[:100].replace("\n", " ")
            print(f"  reply: {reply_preview}…")
        else:
            print(f"✗ [{t['desc']}]")
            print(f"  HTTP {resp.status_code} | očekivano: {t['expect_tool']} | dobio: {tools_used}")
            print(f"  reply: {(data.get('reply') or '')[:120]}")
        print()

    print(f"{'─' * 50}")
    print(f"Rezultat: {passed}/{len(TESTS)}")
    sys.exit(0 if passed == len(TESTS) else 1)


if __name__ == "__main__":
    main()
