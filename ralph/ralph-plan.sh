#!/usr/bin/env bash
# Ručno pokretanje plan moda — jedna iteracija sa PROMPT_plan.md.
# Pokreni kad je Now sekcija prazna ili kad se gomilaju failing entry-ji.
set -euo pipefail
exec env MAX_ITERS=1 PROMPT_FILE=ralph/PROMPT_plan.md bash "$(dirname "$0")/ralph.sh"
