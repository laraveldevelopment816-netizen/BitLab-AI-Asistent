#!/usr/bin/env bash
# Ralph status dashboard — quick pregled sa jednim komandom.
# Pokretanje: bash ralph/status.sh
#
# Pokazuje:
# - Da li Ralph radi sada (proces + trenutna iter)
# - Posljednji log (zadnjih 8 redova)
# - Posljednja 3 commit-a (na ovoj grani)
# - Stanje IMPLEMENTATION_PLAN.md (Now/Done counts)
# - Posljednji eval rezultat (PASS rate iz JSONL-a)

set -euo pipefail

cd "$(dirname "$0")/.."

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; RESET='\033[0m'

echo -e "${CYAN}=== Ralph status — $(date '+%d.%m.%Y %H:%M:%S') ===${RESET}"
echo

# 1. Proces + trenutna iter
echo -e "${CYAN}-- proces --${RESET}"
if pgrep -f "bash ralph/ralph.sh" >/dev/null; then
  echo -e "${GREEN}Ralph RADI${RESET}"
  latest_log=$(ls -t ralph/logs/ralph-*.log 2>/dev/null | head -1 || echo "")
  if [ -n "$latest_log" ]; then
    current_iter=$(grep -E "^Ralph iter " "$latest_log" | tail -1 || echo "(iter X — još nije logovao)")
    # Konvertuj filename timestamp 20260524-072254 u dd.mm.yyyy HH:MM:SS.
    ts_raw=$(head -1 "$latest_log" | grep -oE "[0-9]{8}-[0-9]{6}" || echo "")
    if [ -n "$ts_raw" ]; then
      started_local=$(date -d "${ts_raw:0:4}-${ts_raw:4:2}-${ts_raw:6:2} ${ts_raw:9:2}:${ts_raw:11:2}:${ts_raw:13:2}" '+%d.%m.%Y %H:%M:%S' 2>/dev/null || echo "$ts_raw")
    else
      started_local="?"
    fi
    echo "  log: $latest_log"
    echo "  trenutna: $current_iter"
    echo "  start: $started_local"
  fi
else
  echo -e "${YELLOW}Ralph NE RADI${RESET} (nema bash ralph/ralph.sh procesa)"
  if [ -f ralph/STOP ]; then
    echo -e "  ${YELLOW}STOP marker postoji${RESET} — ukloni sa: rm ralph/STOP"
  fi
fi
echo

# 1b. PAUSE marker — aktivan do <lokalno vrijeme>
if [ -f ralph/PAUSE ]; then
  echo -e "${CYAN}-- PAUSE marker --${RESET}"
  until_epoch=$(grep -oE "^until=[0-9]+" ralph/PAUSE | head -1 | cut -d= -f2 || echo "")
  if [ -n "$until_epoch" ]; then
    until_local=$(date -d "@$until_epoch" '+%d.%m.%Y %H:%M:%S' 2>/dev/null || echo "@$until_epoch")
    now_epoch=$(date +%s)
    if [ "$until_epoch" -le "$now_epoch" ]; then
      echo -e "  ${GREEN}PAUSE istekao${RESET} — sljedeća iter će obrisati marker."
    else
      mins=$(( (until_epoch - now_epoch) / 60 ))
      echo -e "  ${YELLOW}aktivan do $until_local${RESET} (još ~${mins} min)"
    fi
  else
    echo -e "  ${YELLOW}cooperative wait${RESET} — čeka ručni 'rm ralph/PAUSE'"
  fi
  echo
fi

# 2. Posljednji log
echo -e "${CYAN}-- posljednji log (zadnjih 8 redova) --${RESET}"
latest_log=$(ls -t ralph/logs/ralph-*.log 2>/dev/null | head -1 || echo "")
if [ -n "$latest_log" ]; then
  tail -8 "$latest_log" | sed 's/^/  /'
else
  echo "  (nema log-a)"
fi
echo

# 3. Commit-i
echo -e "${CYAN}-- posljednja 3 commit-a (grana $(git branch --show-current)) --${RESET}"
git log --oneline -3 | sed 's/^/  /'
echo

# 4. Plan stanje
echo -e "${CYAN}-- IMPLEMENTATION_PLAN.md --${RESET}"
now_count=$(awk '/^## Now$/,/^## Next$/' ralph/IMPLEMENTATION_PLAN.md | grep -c "^### \|^- \*\*" || echo 0)
done_count=$(awk '/^## Done$/,EOF' ralph/IMPLEMENTATION_PLAN.md | grep -c "^- 2026-" || echo 0)
echo "  Now: $now_count task-ova | Done: $done_count completed"
echo "  Top Now task:"
awk '/^## Now$/,/^## Next$/' ralph/IMPLEMENTATION_PLAN.md | grep -E "^### |^- \*\*" | head -1 | sed 's/^/    /'
echo

# 5. Posljednji eval
echo -e "${CYAN}-- posljednji eval (JSONL summary) --${RESET}"
latest_jsonl=$(ls -t evals/runs/*.jsonl 2>/dev/null | head -1 || echo "")
if [ -n "$latest_jsonl" ]; then
  total=$(wc -l < "$latest_jsonl" | tr -d ' ')
  pass=$(grep -c '"overall": "PASS"' "$latest_jsonl" 2>/dev/null | tr -d '\n' || echo 0)
  fail=$(grep -c '"overall": "FAIL"' "$latest_jsonl" 2>/dev/null | tr -d '\n' || echo 0)
  warn=$(grep -c '"overall": "WARN"' "$latest_jsonl" 2>/dev/null | tr -d '\n' || echo 0)
  if [ "$total" -gt 0 ]; then
    rate=$(awk "BEGIN {printf \"%.1f\", $pass/$total*100}")
  else
    rate="0.0"
  fi
  echo "  fajl: $(basename "$latest_jsonl")"
  echo "  total=$total | PASS=$pass | FAIL=$fail | WARN=$warn | rate=${rate}%"
else
  echo "  (nema eval JSONL-a)"
fi
