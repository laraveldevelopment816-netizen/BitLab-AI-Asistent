#!/usr/bin/env bash
# BitLab AI Asistent — server-side deploy/update skripta
#
# Uloga: ne SSH iz lokalne, ovo se izvršava NA SERVERU od strane
# server-side Claude sesije ili ručno preko sudo bash scripts/deploy.sh.
#
# Usage:
#   bash scripts/deploy.sh install    # prvi install — kreira venv, build, systemd
#   bash scripts/deploy.sh update     # git pull + reinstall deps + rebuild + restart
#   bash scripts/deploy.sh rebuild    # samo dashboard rebuild + nginx reload
#   bash scripts/deploy.sh restart    # samo systemctl restart bitlab-ai
#
# Pretpostavke (provjeri prije install):
# - Linux Debian/Ubuntu (apt-based)
# - Python 3.11+ na sistemu
# - sudo dostupan
# - /opt/bitlab-ai sadrži ovaj git checkout
# - /opt/bitlab-ai/.env popunjen (ANTHROPIC_API_KEY, DASHBOARD_API_KEY...)

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/bitlab-ai}"
SERVICE_USER="${SERVICE_USER:-bitlab}"
DASHBOARD_DIST_TARGET="${DASHBOARD_DIST_TARGET:-/var/www/bitlab-admin}"
SERVICE_NAME="bitlab-ai"

cd "$PROJECT_DIR"

# ── Helpers ─────────────────────────────────────────────────────

log()  { printf '\e[1;36m▶ %s\e[0m\n' "$*"; }
ok()   { printf '\e[1;32m✓ %s\e[0m\n' "$*"; }
warn() { printf '\e[1;33m⚠ %s\e[0m\n' "$*"; }
err()  { printf '\e[1;31m✗ %s\e[0m\n' "$*" >&2; exit 1; }

require_sudo() {
    if [[ $EUID -ne 0 ]]; then
        err "Pokreni preko sudo: sudo bash scripts/deploy.sh $*"
    fi
}

# ── Steps ───────────────────────────────────────────────────────

ensure_user() {
    if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
        log "Kreiram service user-a $SERVICE_USER"
        useradd --system --shell /usr/sbin/nologin --home-dir "$PROJECT_DIR" \
                --no-create-home "$SERVICE_USER"
        ok "User $SERVICE_USER kreiran"
    fi
}

ensure_venv() {
    if [[ ! -d "$PROJECT_DIR/.venv" ]]; then
        log "Kreiram venv u .venv/"
        python3 -m venv "$PROJECT_DIR/.venv"
    fi
    ok "venv ok"
}

install_python_deps() {
    log "Install Python deps (CPU-only torch, ~3 min prvi put)"
    "$PROJECT_DIR/.venv/bin/pip" install --upgrade pip wheel >/dev/null
    "$PROJECT_DIR/.venv/bin/pip" install \
        torch --index-url https://download.pytorch.org/whl/cpu \
        >/dev/null 2>&1 || warn "torch install — ako već instaliran, ignoriši"
    "$PROJECT_DIR/.venv/bin/pip" install -e .
    ok "Python deps OK"
}

ensure_data_files() {
    if [[ ! -f "$PROJECT_DIR/data/products.index.npz" ]]; then
        warn "Nedostaje data/products.index.npz"
        warn "Pokreni: $PROJECT_DIR/.venv/bin/python scripts/embed_products.py"
        warn "(ovo traje ~5 min prvi put — preuzima sentence-transformer model)"
    fi
    if [[ ! -f "$PROJECT_DIR/data/categories.json" ]]; then
        log "Generišem data/categories.json"
        "$PROJECT_DIR/.venv/bin/python" scripts/build_categories.py
    fi
    ok "Data files ok"
}

init_database() {
    log "Init dashboard DB schema"
    mkdir -p "$PROJECT_DIR/var"
    "$PROJECT_DIR/.venv/bin/python" scripts/init_db.py
    ok "DB schema ok"
}

build_dashboard() {
    if ! command -v pnpm >/dev/null 2>&1; then
        if [[ -d "$PROJECT_DIR/dashboard/dist" ]]; then
            warn "pnpm not found — koristim postojeći dashboard/dist (rsync-ovan ručno?)"
            return 0
        fi
        err "pnpm not installed i nema pre-built dist. Install: npm i -g pnpm"
    fi
    log "Build dashboard (Vite + tsc)"
    cd "$PROJECT_DIR/dashboard"
    pnpm install --frozen-lockfile >/dev/null
    pnpm build
    cd "$PROJECT_DIR"
    ok "dashboard/dist build OK"
}

publish_dashboard() {
    require_sudo "$@"
    log "Publish dashboard u $DASHBOARD_DIST_TARGET"
    mkdir -p "$DASHBOARD_DIST_TARGET"
    rsync -a --delete "$PROJECT_DIR/dashboard/dist/" "$DASHBOARD_DIST_TARGET/"
    chown -R www-data:www-data "$DASHBOARD_DIST_TARGET"
    ok "Dashboard published"
}

install_systemd() {
    require_sudo "$@"
    log "Install systemd unit"
    cp "$PROJECT_DIR/deploy/bitlab-ai.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    ok "systemd unit installed + enabled"
}

install_nginx() {
    require_sudo "$@"
    if [[ ! -f /etc/nginx/sites-available/bitlab-ai ]]; then
        warn "nginx site nije postojao — kopiram template"
        warn "MORAŠ ručno zameniti AI_DOMAIN_PLACEHOLDER sa pravim domenom!"
        cp "$PROJECT_DIR/deploy/nginx-site.conf" /etc/nginx/sites-available/bitlab-ai
        warn "Editiraj: sudo nano /etc/nginx/sites-available/bitlab-ai"
    fi
    [[ -L /etc/nginx/sites-enabled/bitlab-ai ]] || \
        ln -s /etc/nginx/sites-available/bitlab-ai /etc/nginx/sites-enabled/

    if nginx -t 2>&1 | grep -q "syntax is ok"; then
        systemctl reload nginx
        ok "nginx reload"
    else
        warn "nginx config ima sintaksnu grešku — provjeri sudo nginx -t"
    fi
}

restart_service() {
    require_sudo "$@"
    log "Restart $SERVICE_NAME"
    systemctl restart "$SERVICE_NAME"
    sleep 3
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        ok "$SERVICE_NAME active"
    else
        warn "Service nije active — provjeri: journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

smoke_test() {
    log "Smoke test"
    if curl -fsS http://127.0.0.1:8000/healthz | grep -q '"status":"ok"'; then
        ok "/healthz OK"
    else
        warn "/healthz nije ok"
        return 1
    fi
    if [[ -n "${DASHBOARD_API_KEY:-}" ]]; then
        if curl -fsS -H "Authorization: Bearer $DASHBOARD_API_KEY" \
             http://127.0.0.1:8000/api/dashboard/stats | grep -q "total_requests"; then
            ok "/api/dashboard/stats OK (auth radi)"
        else
            warn "/api/dashboard/stats — provjeri DASHBOARD_API_KEY"
        fi
    else
        warn "DASHBOARD_API_KEY nije u env-u (probaj: source .env)"
    fi
}

# ── Commands ───────────────────────────────────────────────────

cmd_install() {
    require_sudo "$@"
    log "FRESH INSTALL u $PROJECT_DIR"
    ensure_user
    chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_DIR"
    sudo -u "$SERVICE_USER" bash -c "
        cd $PROJECT_DIR
        $(declare -f log ok warn err ensure_venv install_python_deps ensure_data_files init_database)
        ensure_venv
        install_python_deps
        ensure_data_files
        init_database
    "
    build_dashboard
    publish_dashboard
    install_systemd
    install_nginx
    restart_service
    smoke_test
    ok "INSTALL DONE"
    echo
    echo "Sledeći koraci:"
    echo "  1. sudo nano /etc/nginx/sites-available/bitlab-ai  (zameni AI_DOMAIN_PLACEHOLDER)"
    echo "  2. sudo certbot --nginx -d <tvoj-domen>"
    echo "  3. sudo systemctl reload nginx"
    echo "  4. https://<tvoj-domen>/admin/  → unesi DASHBOARD_API_KEY u Settings"
}

cmd_update() {
    require_sudo "$@"
    log "UPDATE flow"
    sudo -u "$SERVICE_USER" git -C "$PROJECT_DIR" pull --ff-only
    sudo -u "$SERVICE_USER" bash -c "
        cd $PROJECT_DIR
        $(declare -f log ok warn err install_python_deps ensure_data_files init_database)
        install_python_deps
        ensure_data_files
        init_database
    "
    build_dashboard
    publish_dashboard
    restart_service
    smoke_test
    ok "UPDATE DONE"
}

cmd_rebuild() {
    require_sudo "$@"
    log "REBUILD dashboard only"
    build_dashboard
    publish_dashboard
    ok "REBUILD DONE"
}

cmd_restart() {
    require_sudo "$@"
    restart_service
    smoke_test
}

# ── Main ───────────────────────────────────────────────────────

case "${1:-}" in
    install) shift; cmd_install "$@" ;;
    update)  shift; cmd_update  "$@" ;;
    rebuild) shift; cmd_rebuild "$@" ;;
    restart) shift; cmd_restart "$@" ;;
    *)
        cat <<EOF
Usage: sudo bash scripts/deploy.sh <command>

Commands:
  install   Prvi install (venv, deps, systemd, nginx)
  update    git pull + reinstall + rebuild + restart
  rebuild   Samo rebuild dashboard-a + publish
  restart   Samo systemctl restart bitlab-ai

Environment overrides:
  PROJECT_DIR             default: /opt/bitlab-ai
  SERVICE_USER            default: bitlab
  DASHBOARD_DIST_TARGET   default: /var/www/bitlab-admin
EOF
        exit 1
        ;;
esac
