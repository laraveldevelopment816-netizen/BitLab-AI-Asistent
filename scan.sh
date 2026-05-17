#!/usr/bin/env bash
# Skenira tekući git repo u jedan fajl — struktura + sadržaj svih tracked
# tekstualnih fajlova. Za lijepljenje online agentu (deep research).
# Upotreba:  ./scan.sh [output-fajl]   (default: repo-scan.md)
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
OUT="${1:-repo-scan.md}"

{
  echo "# BitLab AI Asistent"
  echo
  echo "- Datum:  $(date -u +%Y-%m-%dT%H:%MZ)"
  echo "- Remote: $(git remote get-url origin 2>/dev/null || echo n/a)"
  echo "- Branch: $(git branch --show-current 2>/dev/null || echo n/a)"
  echo "- Commit: $(git rev-parse --short HEAD 2>/dev/null || echo n/a)"
  echo
  echo "## Struktura"
  echo
  git ls-files --cached --others --exclude-standard
  echo
  echo "## Sadržaj fajlova"
  echo
  git ls-files --cached --others --exclude-standard -z | while IFS= read -r -d '' f; do
    if file --mime-encoding "$f" 2>/dev/null | grep -q binary; then
      printf '===== FILE: %s (binarni, preskočeno) =====\n\n' "$f"
      continue
    fi
    printf '===== FILE: %s =====\n' "$f"
    cat "$f"
    printf '\n===== END: %s =====\n\n' "$f"
  done
} > "$OUT"

echo "Gotovo: $OUT ($(wc -l < "$OUT") linija, $(git ls-files --cached --others --exclude-standard | wc -l) fajlova)"
