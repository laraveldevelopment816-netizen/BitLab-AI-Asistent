"""
Eval runner — pokreće 18 pitanja kroz API i ispisuje pass/fail tabelu.

Server mora biti pokrenut:
    uvicorn app.main:app --reload

Pokretanje:
    python evals/run.py
    python evals/run.py --url http://ai.bitlab.rs  # produkcija
    python evals/run.py --channel email            # samo email pitanja
    python evals/run.py --verbose                  # ispiši odgovore
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = EVALS_DIR / "test_questions.json"

DEFAULT_URL = "http://localhost:8000"
TIMEOUT_S = 60


def _post(base_url: str, message: str, channel: str) -> tuple[dict, float]:
    """Pošalje POST na /api/chat, vrati (response_dict, latency_s)."""
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = json.dumps({"message": message, "channel": channel}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = resp.read()
        latency = time.perf_counter() - t0
        return json.loads(body), latency
    except urllib.error.URLError as e:
        raise SystemExit(
            f"\nGreška: server nije dostupan na {url}\n"
            f"  Provjeri: uvicorn app.main:app --reload\n"
            f"  Detalj: {e}"
        ) from e


def _check(result: dict, q: dict) -> tuple[bool, list[str]]:
    """Provjeri pass/fail kriterije. Vrati (passed, lista_razloga_pada)."""
    failures: list[str] = []
    tools_used: list[str] = result.get("tools_used", [])
    reply: str = result.get("reply", "")
    reply_lower = reply.lower()

    # Provjera alata
    expect_tool = q.get("expect_tool")
    if expect_tool is not None:
        if expect_tool not in tools_used:
            failures.append(f"expect_tool={expect_tool!r} nije pozvan (korišteni: {tools_used})")
    else:
        # Pitanje ne smije pozvati nikakav alat (npr. prompt injection)
        if tools_used:
            failures.append(f"očekivano 0 alata, korišten: {tools_used}")

    # Provjera sadržaja odgovora
    for expected in q.get("expect_contains", []):
        if expected.lower() not in reply_lower:
            failures.append(f"reply ne sadrži '{expected}'")

    for forbidden in q.get("expect_not_contains", []):
        if forbidden.lower() in reply_lower:
            failures.append(f"reply SADRŽI zabranjeno '{forbidden}'")

    return len(failures) == 0, failures


def _truncate(text: str, n: int = 80) -> str:
    text = text.replace("\n", " ")
    return text[:n] + "…" if len(text) > n else text


def run(base_url: str, channel_filter: str | None, verbose: bool) -> int:
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))

    if channel_filter:
        questions = [q for q in questions if q.get("channel", "chat") == channel_filter]

    if not questions:
        print(f"Nema pitanja za kanal '{channel_filter}'.")
        return 0

    print(f"\nBitLab eval → {base_url}/api/chat")
    print(f"Pitanja: {len(questions)}")
    print("─" * 90)

    # Zaglavlje
    col_q   = 44
    col_t   = 20
    col_r   = 6
    col_lat = 7
    header = (
        f"{'#':<4} {'Pitanje':<{col_q}} {'Alati':<{col_t}} {'Res':>{col_r}} {'ms':>{col_lat}}"
    )
    print(header)
    print("─" * 90)

    passed = 0
    failed = 0
    skipped = 0

    for q in questions:
        qid = q["id"]
        question = q["q"]
        channel = q.get("channel", "chat")

        try:
            result, latency = _post(base_url, question, channel)
        except KeyboardInterrupt:
            print("\nPrekinuto.")
            break
        except Exception as exc:
            print(f"{qid:<4} {'[GREŠKA]':<{col_q}} {str(exc)[:col_t]:<{col_t}} {'ERR':>{col_r}} {'—':>{col_lat}}")
            skipped += 1
            continue

        ok, failures = _check(result, q)
        tools_str = ",".join(result.get("tools_used", []) or ["—"])
        lat_ms = int(latency * 1000)
        res_str = "✓" if ok else "✗"

        q_short = _truncate(f"[{channel}] {question}", col_q)
        print(
            f"{qid:<4} {q_short:<{col_q}} {tools_str:<{col_t}} {res_str:>{col_r}} {lat_ms:>{col_lat}}"
        )

        if not ok:
            for reason in failures:
                print(f"       ↳ {reason}")

        if verbose:
            print(f"       Reply: {_truncate(result.get('reply', ''), 120)}")

        if ok:
            passed += 1
        else:
            failed += 1

    print("─" * 90)
    total = passed + failed + skipped
    print(f"Rezultat: {passed}/{total} prošlo  ({failed} palo, {skipped} greška)\n")

    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="BitLab eval runner")
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--channel", default=None, help="Filtriraj po kanalu: chat|voice|email")
    parser.add_argument("--verbose", action="store_true", help="Ispiši odgovore")
    args = parser.parse_args()

    sys.exit(run(args.url, args.channel, args.verbose))


if __name__ == "__main__":
    main()
