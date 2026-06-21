#!/usr/bin/env bash
# Prođe cijeli categories acceptance set (250) bez nadzora:
#   petlja → ~80 case-ova po prolazu (≈80% PWR sesije) → sačeka 5h da se sesija
#   resetuje → nastavi odakle je stao (runner --resume). Sve u jedan fajl.
# Pusti pod nohup pa zaboravi:
#   nohup bash scripts/run_acceptance.sh > evals/runs/acpt-run.log 2>&1 & disown
set -euo pipefail
cd "$(dirname "$0")/.."

URL="http://localhost:7778"
JSONL="evals/runs/categories-acpt.jsonl"
BATCH=80                     # case-ova po prolazu (≈80% sesije)
RESET_SLEEP=$((5 * 3600))    # 5h — dok se PWR sesija ne resetuje

# Server mora biti gore — inače runner upiše lažne FAIL-ove u fajl.
curl -sf -o /dev/null --max-time 3 "$URL/healthz" || {
  echo "Server nije gore. Pokreni:  .venv/bin/uvicorn app.main:app --port 7778" >&2
  exit 1
}

while true; do
  done_n=0; [ -f "$JSONL" ] && done_n=$(grep -c . "$JSONL" || true)
  [ "$done_n" -ge 250 ] && { echo "GOTOVO — ${done_n}/250. Rezultati: ${JSONL}"; break; }

  echo "[$(date '+%H:%M')] ${done_n}/250 — radim još ~${BATCH}..."
  set +e
  .venv/bin/python -m evals.framework.runner \
    --suite categories --mode full --label acpt --resume acpt \
    --no-cache --max-calls 100000 --limit $((done_n + BATCH)) --url "$URL"
  rc=$?            # 0/1 = prolaz gotov · 3 = PWR limit (nastavi poslije pauze) · 2 = nema suite
  set -e
  # --max-calls visok namjerno: veličinu prolaza drži --limit (80 case-ova),
  # ne stari konzervativni 52-poziva gate iz budget.py.
  [ "$rc" = "2" ] && { echo "Suite 'categories' ne postoji (exit 2)." >&2; exit 2; }

  done_n=$(grep -c . "$JSONL" 2>/dev/null || echo 0)
  [ "$done_n" -ge 250 ] && { echo "GOTOVO — ${done_n}/250. Rezultati: ${JSONL}"; break; }

  echo "[$(date '+%H:%M')] ${done_n}/250 — sesija iscrpljena, čekam 5h pa nastavljam..."
  sleep "$RESET_SLEEP"
done
