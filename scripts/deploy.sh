#!/usr/bin/env bash
# scripts/deploy.sh — release-symlink deploy za projekte na ai.bitlab.rs
#
# Pattern: /home/ai/<PROJECT>/{releases/<TS>/, shared/, current → releases/<TS>}
# Detalji: docs/operations/server-conventions.md
#
# Komande:
#   release    Novi release: clone → simlinkuj → install → migracije → build → switch → restart → health → cleanup
#   rollback   Switch na prethodni release + restart
#
# Required env:
#   PROJECT_NAME   Folder pod /home/ai/ (npr. aiasistent-staging)
#   DOMAIN         FQDN za health check (npr. staging.aiasistent.bitlab.rs)
#   PORT           App port (127.0.0.1 only, npr. 8001)
#   REPO_URL       Git URL (SSH preferable)
#   BRANCH         Git branch
#
# Optional env:
#   KEEP_RELEASES  Koliko release-ova zadržati u releases/ (default 5)
#
# Primjer:
#   PROJECT_NAME=aiasistent-staging \
#   DOMAIN=staging.aiasistent.bitlab.rs \
#   PORT=8001 \
#   REPO_URL=git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git \
#   BRANCH=staging \
#   bash scripts/deploy.sh release

set -euo pipefail

# ── Required env ────────────────────────────────────────────────
: "${PROJECT_NAME:?PROJECT_NAME nije set}"
: "${DOMAIN:?DOMAIN nije set}"
: "${PORT:?PORT nije set}"
: "${REPO_URL:?REPO_URL nije set}"
: "${BRANCH:?BRANCH nije set}"

PROJECT_DIR="/home/ai/$PROJECT_NAME"
SHARED_DIR="$PROJECT_DIR/shared"
RELEASES_DIR="$PROJECT_DIR/releases"
KEEP_RELEASES="${KEEP_RELEASES:-5}"

# Globalne (popunjavaju se u clone_release)
RELEASE=""
RELEASE_DIR=""

# ── Helpers ─────────────────────────────────────────────────────
log()  { printf '\e[1;36m▶ %s\e[0m\n' "$*"; }
ok()   { printf '\e[1;32m✓ %s\e[0m\n' "$*"; }
warn() { printf '\e[1;33m⚠ %s\e[0m\n' "$*"; }
err()  { printf '\e[1;31m✗ %s\e[0m\n' "$*" >&2; exit 1; }

# ── Pre-checks ──────────────────────────────────────────────────
pre_checks() {
    log "Pre-checks za $PROJECT_NAME"
    [[ -d "$PROJECT_DIR" ]]      || err "$PROJECT_DIR ne postoji — pokreni setup-domain prvo (Faza B)"
    [[ -L "$PROJECT_DIR/current" ]] || err "$PROJECT_DIR/current symlink ne postoji — projekat nije inicijalizovan"
    [[ -f "$SHARED_DIR/.env" ]]  || err "$SHARED_DIR/.env ne postoji"
    [[ -d "$SHARED_DIR/var" ]]   || err "$SHARED_DIR/var ne postoji"
    if ! systemctl is-active --quiet "$PROJECT_NAME"; then
        warn "$PROJECT_NAME servis nije aktivan trenutno — restart u koraku 8"
    fi
    ok "current → $(basename "$(readlink -f "$PROJECT_DIR/current")")"
}

# ── A.2 Clone ───────────────────────────────────────────────────
clone_release() {
    RELEASE=$(date +%Y%m%d_%H%M)
    RELEASE_DIR="$RELEASES_DIR/$RELEASE"
    [[ -d "$RELEASE_DIR" ]] && err "$RELEASE_DIR već postoji (sačekaj minut)"
    log "Clone $BRANCH u releases/$RELEASE"
    git clone --quiet -b "$BRANCH" "$REPO_URL" "$RELEASE_DIR"
    ok "Clone done — $(cd "$RELEASE_DIR" && git log -1 --oneline)"
}

# ── A.3 Symlinkovi shared resources ─────────────────────────────
link_shared() {
    log "Symlink shared resources"
    ln -sfn "$SHARED_DIR/.env" "$RELEASE_DIR/.env"
    ln -sfn "$SHARED_DIR/var" "$RELEASE_DIR/var"
    ln -sfn "$SHARED_DIR/var/products.index.npz" "$RELEASE_DIR/data/products.index.npz"
    ln -sfn "$SHARED_DIR/var/products.meta.json" "$RELEASE_DIR/data/products.meta.json"
    ok "Simlinkovi: .env, var, data/products.{index.npz,meta.json}"
}

# ── A.4 Python venv + deps ──────────────────────────────────────
install_python_deps() {
    log "Python venv + deps (CPU torch ~2-3 min prvi put)"
    cd "$RELEASE_DIR"
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip wheel >/dev/null
    .venv/bin/pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu >/dev/null
    ok "deps OK ($(du -sh .venv | cut -f1))"
}

# ── A.5 Migracije ───────────────────────────────────────────────
run_migrations() {
    log "Migracije"
    cd "$RELEASE_DIR"
    .venv/bin/python scripts/init_db.py
    .venv/bin/python scripts/migrate_session_id.py
    .venv/bin/python scripts/build_categories.py
    ok "Migracije done"
}

# ── A.6 Dashboard build + API key injection ────────────────────
build_dashboard() {
    if ! command -v pnpm >/dev/null 2>&1; then
        err "pnpm nije instaliran (sudo corepack enable; sudo corepack prepare pnpm@10 --activate)"
    fi
    log "Dashboard build (Vite)"
    cd "$RELEASE_DIR/dashboard"
    pnpm install --frozen-lockfile --silent
    pnpm build
    [[ -f dist/index.html ]] || err "build pao — nema dist/index.html"

    # Inject DASHBOARD_API_KEY u dist/index.html (auto-config za /admin/).
    # Placeholder __BITLAB_DASHBOARD_KEY_PLACEHOLDER__ je u dashboard/index.html.
    local key
    key=$(grep ^DASHBOARD_API_KEY "$SHARED_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'")
    if [[ -z "$key" ]]; then
        warn "DASHBOARD_API_KEY nije u shared/.env — dashboard će tražiti ručni paste u Settings"
    else
        sed -i "s|__BITLAB_DASHBOARD_KEY_PLACEHOLDER__|$key|" "$RELEASE_DIR/dashboard/dist/index.html"
        if grep -q "__BITLAB_DASHBOARD_KEY_PLACEHOLDER__" "$RELEASE_DIR/dashboard/dist/index.html"; then
            warn "Placeholder još uvijek u dist/index.html — provjeri sed output"
        else
            ok "DASHBOARD_API_KEY injektovan u dist/index.html"
        fi
    fi

    ok "dashboard/dist OK ($(du -sh dist | cut -f1))"
}

# ── A.7 Atomic switch ──────────────────────────────────────────
atomic_switch() {
    local prev
    prev=$(basename "$(readlink -f "$PROJECT_DIR/current" 2>/dev/null || echo none)")
    log "Atomic switch: $prev → $RELEASE"
    ln -sfn "$RELEASE_DIR" "$PROJECT_DIR/current"
    ok "current → $RELEASE"
}

# ── A.8 Restart ─────────────────────────────────────────────────
restart_service() {
    log "Restart $PROJECT_NAME"
    sudo systemctl restart "$PROJECT_NAME"
    sleep 5
    if systemctl is-active --quiet "$PROJECT_NAME"; then
        ok "$PROJECT_NAME active (PID $(systemctl show -p MainPID --value "$PROJECT_NAME"))"
    else
        sudo journalctl -u "$PROJECT_NAME" -n 30 --no-pager
        err "Servis nije aktivan posle restart-a"
    fi
}

# ── A.9 Health check ───────────────────────────────────────────
health_check() {
    log "Health check"
    local resp
    resp=$(curl -sf "http://127.0.0.1:$PORT/healthz") || err "/healthz lokalno FAIL"
    resp=$(curl -sf "https://$DOMAIN/healthz") || err "/healthz HTTPS FAIL"
    echo "  → $resp"
    echo "$resp" | grep -q '"products_index_present":true' \
        && ok "products_index" \
        || warn "products_index NIJE prisutan"

    # Dashboard stats (auth + DB konekcija)
    local key
    key=$(grep ^DASHBOARD_API_KEY "$SHARED_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "")
    if [[ -n "$key" ]]; then
        if curl -sf -H "Authorization: Bearer $key" "http://127.0.0.1:$PORT/api/dashboard/stats" >/dev/null; then
            ok "Dashboard stats endpoint OK (auth + DB)"
        else
            warn "Dashboard stats failuje — provjeri DASHBOARD_API_KEY i DB"
        fi
    fi

    # Errori u logu od restart-a
    if sudo journalctl -u "$PROJECT_NAME" --since "1 min ago" --no-pager 2>/dev/null \
         | grep -iqE 'error|traceback'; then
        warn "Errori u logu zadnji minut — provjeri: sudo journalctl -u $PROJECT_NAME -n 50"
    else
        ok "Logovi clean (zadnji minut)"
    fi
}

# ── A.10 Cleanup ───────────────────────────────────────────────
cleanup_old() {
    log "Cleanup — držimo zadnjih $KEEP_RELEASES release-ova"
    local to_delete count=0
    to_delete=$(ls -t "$RELEASES_DIR" | tail -n +$((KEEP_RELEASES + 1)))
    if [[ -z "$to_delete" ]]; then
        ok "Manje od $KEEP_RELEASES release-ova — ništa se ne briše"
        return
    fi
    while IFS= read -r d; do
        rm -rf "${RELEASES_DIR:?}/$d"
        ok "Obrisan release $d"
        count=$((count + 1))
    done <<< "$to_delete"
    ok "Cleanup done ($count obrisano)"
}

# ── Rollback ───────────────────────────────────────────────────
do_rollback() {
    log "Rollback $PROJECT_NAME"
    [[ -L "$PROJECT_DIR/current" ]] || err "current symlink ne postoji"
    local current_release prev
    current_release=$(basename "$(readlink -f "$PROJECT_DIR/current")")
    prev=$(ls -t "$RELEASES_DIR" | grep -v "^${current_release}\$" | head -1)
    [[ -n "$prev" ]] || err "Nema prethodnog release-a (samo $current_release postoji)"
    log "Switch: $current_release → $prev"
    ln -sfn "$RELEASES_DIR/$prev" "$PROJECT_DIR/current"
    sudo systemctl restart "$PROJECT_NAME"
    sleep 5
    systemctl is-active --quiet "$PROJECT_NAME" && ok "Rollback aktivan ($prev)" \
        || err "Servis nije aktivan posle rollback-a"
    curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null && ok "Health check OK" \
        || warn "Health check failuje"
}

# ── Main ───────────────────────────────────────────────────────
case "${1:-}" in
    release)
        log "RELEASE flow za $PROJECT_NAME ($BRANCH)"
        pre_checks
        clone_release
        link_shared
        install_python_deps
        run_migrations
        build_dashboard
        atomic_switch
        restart_service
        health_check
        cleanup_old
        echo
        ok "RELEASE $RELEASE AKTIVAN — https://$DOMAIN/healthz"
        ;;
    rollback)
        do_rollback
        ;;
    *)
        sed -n '2,30p' "$0"
        exit 1
        ;;
esac
