#!/usr/bin/env bash
# Ralph petlja — stateless loop. Čita PROMPT_build.md i feed-uje Claude-u dok
# ne postoji ralph/STOP marker fajl ili dok ne dosegne MAX_ITERS.
#
# Pokretanje:
#   bash ralph/ralph.sh                    # default MAX_ITERS=100
#   MAX_ITERS=50 bash ralph/ralph.sh
#   touch ralph/STOP                       # zaustavi petlju (iz drugog terminala)
#   touch ralph/PAUSE                      # cooperative pauza (čeka rm)
#   echo "until=$(date -d '+1h' +%s)" > ralph/PAUSE   # auto-resume nakon 1h
#
# Eval runner (--exit kod 3) sam piše ralph/PAUSE sa until=<epoch> kad lupi
# rate limit ili budget pređe 65% MAX_CALLS. Ralph na sljedećoj iteraciji
# detektuje PAUSE i čeka (poll svakih 300s) dok marker ne nestane ili until
# ne istekne. PAUSE bez until = beskonačno čekanje rm.
#
# Logovi: ralph/logs/ralph-<timestamp>.log

set -euo pipefail

MAX_ITERS="${MAX_ITERS:-100}"
SLEEP_BETWEEN="${SLEEP_BETWEEN:-3}"
PROMPT_FILE="${PROMPT_FILE:-ralph/PROMPT_build.md}"

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "FATAL: $PROMPT_FILE ne postoji u $(pwd)." >&2
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "FATAL: 'claude' CLI nije u PATH. Instaliraj Claude Code prvo." >&2
  exit 1
fi

# Python interpreter za wait_pause + estimate_reset helpere.
PY="${PY:-.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "FATAL: $PY ne postoji. Aktiviraj venv ili setuj PY env var." >&2
  exit 1
fi

mkdir -p ralph/logs
log_file="ralph/logs/ralph-$(date +%Y%m%d-%H%M%S).log"
echo "Ralph start: prompt=$PROMPT_FILE max_iters=$MAX_ITERS log=$log_file" | tee "$log_file"

iter=0
while [ "$iter" -lt "$MAX_ITERS" ]; do
  if [ -f ralph/STOP ]; then
    echo "STOP marker pronađen — izlazim. Iteracija: $iter." | tee -a "$log_file"
    exit 0
  fi

  # PAUSE marker — auto-resume nakon until=<epoch> ili cooperative wait do rm.
  if [ -f ralph/PAUSE ]; then
    echo "[pause] PAUSE marker pronađen, pozivam wait_pause helper..." | tee -a "$log_file"
    if ! "$PY" ralph/wait_pause.py; then
      echo "[pause] STOP tokom čekanja — izlazim." | tee -a "$log_file"
      exit 0
    fi
    echo "[pause] nastavljam." | tee -a "$log_file"
  fi

  iter=$((iter + 1))
  {
    echo "============================================================"
    echo "Ralph iter $iter / $MAX_ITERS — $(date -Iseconds)"
    echo "============================================================"
  } | tee -a "$log_file"
  # `claude --print` čita stdin kao prompt, izvršava jednom, izlazi.
  # `--dangerously-skip-permissions` jer je Ralph autonomic — korisnik je
  # dao pristanak pokretanjem ovog skripta.
  cat "$PROMPT_FILE" | claude --print --dangerously-skip-permissions 2>&1 | tee -a "$log_file"
  CLAUDE_EXIT=${PIPESTATUS[1]}

  # Ako eval runner kroz Claude exit-ovao sa kodom 3 (rate limit ili budget),
  # eval runner je već napisao ralph/PAUSE sa until=<epoch> i checkpoint sa
  # next_index. Ne radimo ovdje ništa dodatno — sljedeća iteracija detektuje
  # PAUSE i čeka. Ali ako iz nekog razloga PAUSE nije napisan (npr. mock test),
  # estimate_reset helper postavlja fallback PAUSE sa now+5h.
  if [ "$CLAUDE_EXIT" = "3" ] && [ ! -f ralph/PAUSE ]; then
    UNTIL=$("$PY" ralph/estimate_reset.py)
    echo "until=$UNTIL" > ralph/PAUSE
    echo "reason=claude exit 3 (no PAUSE marker, fallback estimate)" >> ralph/PAUSE
    UNTIL_LOCAL=$(date -d "@$UNTIL" '+%d.%m.%Y %H:%M:%S')
    echo "[ralph] claude exit 3 → fallback PAUSE marker, aktivan do $UNTIL_LOCAL" | tee -a "$log_file"
  fi

  sleep "$SLEEP_BETWEEN"
done

echo "MAX_ITERS ($MAX_ITERS) dostignut. Provjeri $log_file." | tee -a "$log_file"
