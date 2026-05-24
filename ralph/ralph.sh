#!/usr/bin/env bash
# Ralph petlja — stateless loop. Čita PROMPT_build.md i feed-uje Claude-u dok
# ne postoji ralph/STOP marker fajl ili dok ne dosegne MAX_ITERS.
#
# Pokretanje:
#   bash ralph/ralph.sh                    # default MAX_ITERS=20
#   MAX_ITERS=50 bash ralph/ralph.sh
#   touch ralph/STOP                       # zaustavi petlju (iz drugog terminala)
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

mkdir -p ralph/logs
log_file="ralph/logs/ralph-$(date +%Y%m%d-%H%M%S).log"
echo "Ralph start: prompt=$PROMPT_FILE max_iters=$MAX_ITERS log=$log_file" | tee "$log_file"

iter=0
while [ "$iter" -lt "$MAX_ITERS" ]; do
  if [ -f ralph/STOP ]; then
    echo "STOP marker pronađen — izlazim. Iteracija: $iter." | tee -a "$log_file"
    exit 0
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
  sleep "$SLEEP_BETWEEN"
done

echo "MAX_ITERS ($MAX_ITERS) dostignut. Provjeri $log_file." | tee -a "$log_file"
