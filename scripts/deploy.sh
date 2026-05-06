#!/usr/bin/env bash
# scripts/deploy.sh — release-symlink deploy + domain setup za projekte na ai.bitlab.rs
#
# Pattern: /home/ai/<PROJECT>/{releases/<TS>/, shared/, current → releases/<TS>}
# Detalji: docs/operations/server-conventions.md
#
# Komande:
#   release         Novi release (postojeći projekat): clone → install → migracije → build → switch → restart → health → cleanup
#   rollback        Switch na prethodni release + restart
#   setup-domain    Inicijalni setup novog projekta: pre-checks → folderi → .env → release → systemd → nginx → SSL → health
#
# Required env (release & rollback):
#   PROJECT_NAME, DOMAIN, PORT, REPO_URL, BRANCH
#
# Required env (setup-domain — dodatno):
#   ENTRY_POINT     uvicorn module (npr. app.main:app)
#   ADMIN_EMAIL     Email za certbot (npr. admin@bitlab.rs)
#
# Optional env:
#   KEEP_RELEASES   Default 5
#   RUN_USER        Default ai
#   ENV_TEMPLATE    Path do template .env-a — ako nije set, pravi prazan placeholder i staje
#   SKIP_SSL        Default 0; 1 znači preskoči certbot (kad DNS još nije propagirao)
#
# Primjer setup-domain za aiasistent-prod:
#   source ~/aiasistent-prod.env
#   bash scripts/deploy.sh setup-domain

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
RUN_USER="${RUN_USER:-ai}"
SKIP_SSL="${SKIP_SSL:-0}"

# Globalne (popunjavaju se u clone_release)
RELEASE=""
RELEASE_DIR=""

# ── Helpers ─────────────────────────────────────────────────────
log()  { printf '\e[1;36m▶ %s\e[0m\n' "$*"; }
ok()   { printf '\e[1;32m✓ %s\e[0m\n' "$*"; }
warn() { printf '\e[1;33m⚠ %s\e[0m\n' "$*"; }
err()  { printf '\e[1;31m✗ %s\e[0m\n' "$*" >&2; exit 1; }

# ════════════════════════════════════════════════════════════════
# RELEASE flow (postojeći projekat) — A.* iz DEPLOY.md
# ════════════════════════════════════════════════════════════════

pre_checks() {
    log "Pre-checks za $PROJECT_NAME"
    [[ -d "$PROJECT_DIR" ]]      || err "$PROJECT_DIR ne postoji — pokreni 'setup-domain' prvo"
    [[ -L "$PROJECT_DIR/current" ]] || err "$PROJECT_DIR/current symlink ne postoji — projekat nije inicijalizovan"
    [[ -f "$SHARED_DIR/.env" ]]  || err "$SHARED_DIR/.env ne postoji"
    [[ -d "$SHARED_DIR/var" ]]   || err "$SHARED_DIR/var ne postoji"
    if ! systemctl is-active --quiet "$PROJECT_NAME"; then
        warn "$PROJECT_NAME servis nije aktivan trenutno — restart u koraku 8"
    fi
    ok "current → $(basename "$(readlink -f "$PROJECT_DIR/current")")"
}

clone_release() {
    RELEASE=$(date +%Y%m%d_%H%M)
    RELEASE_DIR="$RELEASES_DIR/$RELEASE"
    [[ -d "$RELEASE_DIR" ]] && err "$RELEASE_DIR već postoji (sačekaj minut)"
    log "Clone $BRANCH u releases/$RELEASE"
    git clone --quiet -b "$BRANCH" "$REPO_URL" "$RELEASE_DIR"
    ok "Clone done — $(cd "$RELEASE_DIR" && git log -1 --oneline)"
}

link_shared() {
    log "Symlink shared resources"
    ln -sfn "$SHARED_DIR/.env" "$RELEASE_DIR/.env"
    ln -sfn "$SHARED_DIR/var" "$RELEASE_DIR/var"
    # data/products.* su aiasistent-specific — preskači ako data/ ne postoji u releaseu
    if [[ -d "$RELEASE_DIR/data" ]]; then
        ln -sfn "$SHARED_DIR/var/products.index.npz" "$RELEASE_DIR/data/products.index.npz"
        ln -sfn "$SHARED_DIR/var/products.meta.json" "$RELEASE_DIR/data/products.meta.json"
    fi
    ok "Simlinkovi: .env, var$([[ -d "$RELEASE_DIR/data" ]] && echo ', data/products.{index,meta}')"
}

install_python_deps() {
    log "Python venv + deps (CPU torch ~2-3 min prvi put)"
    cd "$RELEASE_DIR"
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip wheel >/dev/null
    .venv/bin/pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu >/dev/null
    ok "deps OK ($(du -sh .venv | cut -f1))"
}

run_migrations() {
    log "Migracije"
    cd "$RELEASE_DIR"
    # Idempotentne i opcione — preskači ako skripta ne postoji u projektu
    [[ -f scripts/init_db.py ]]            && .venv/bin/python scripts/init_db.py            || true
    [[ -f scripts/migrate_session_id.py ]] && .venv/bin/python scripts/migrate_session_id.py || true
    [[ -f scripts/build_categories.py ]]   && .venv/bin/python scripts/build_categories.py   || true
    ok "Migracije done"
}

build_dashboard() {
    if [[ ! -d "$RELEASE_DIR/dashboard" ]]; then
        ok "Dashboard build preskočen (nema dashboard/ folder)"
        return
    fi
    if ! command -v pnpm >/dev/null 2>&1; then
        err "pnpm nije instaliran (sudo corepack enable; sudo corepack prepare pnpm@10 --activate)"
    fi
    log "Dashboard build (Vite)"
    cd "$RELEASE_DIR/dashboard"
    pnpm install --frozen-lockfile --silent
    pnpm build
    [[ -f dist/index.html ]] || err "build pao — nema dist/index.html"

    # Inject DASHBOARD_API_KEY u dist/index.html (auto-config za /admin/)
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

atomic_switch() {
    local prev
    prev=$(basename "$(readlink -f "$PROJECT_DIR/current" 2>/dev/null || echo none)")
    log "Atomic switch: $prev → $RELEASE"
    ln -sfn "$RELEASE_DIR" "$PROJECT_DIR/current"
    ok "current → $RELEASE"
}

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

health_check() {
    log "Health check"
    local resp
    resp=$(curl -sf "http://127.0.0.1:$PORT/healthz") || err "/healthz lokalno FAIL"
    resp=$(curl -sf "https://$DOMAIN/healthz") || err "/healthz HTTPS FAIL"
    echo "  → $resp"
    echo "$resp" | grep -q '"products_index_present":true' \
        && ok "products_index" \
        || warn "products_index NIJE prisutan (OK ako projekat nema RAG index)"

    local key
    key=$(grep ^DASHBOARD_API_KEY "$SHARED_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "")
    if [[ -n "$key" ]]; then
        if curl -sf -H "Authorization: Bearer $key" "http://127.0.0.1:$PORT/api/dashboard/stats" >/dev/null; then
            ok "Dashboard stats endpoint OK (auth + DB)"
        else
            warn "Dashboard stats failuje — provjeri DASHBOARD_API_KEY i DB"
        fi
    fi

    if sudo journalctl -u "$PROJECT_NAME" --since "1 min ago" --no-pager 2>/dev/null \
         | grep -iqE 'error|traceback'; then
        warn "Errori u logu zadnji minut — provjeri: sudo journalctl -u $PROJECT_NAME -n 50"
    else
        ok "Logovi clean (zadnji minut)"
    fi
}

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

# ════════════════════════════════════════════════════════════════
# ROLLBACK
# ════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════
# SETUP-DOMAIN flow (novi projekat / domen) — B.* iz DEPLOY.md
# ════════════════════════════════════════════════════════════════

setup_pre_checks() {
    log "Setup pre-checks za $PROJECT_NAME → $DOMAIN:$PORT"

    # Required env za setup-domain
    : "${ENTRY_POINT:?ENTRY_POINT nije set (npr. app.main:app)}"
    : "${ADMIN_EMAIL:?ADMIN_EMAIL nije set (potreban za certbot)}"

    # Project folder: ako 'current' postoji → projekat je već inicijalizovan
    if [[ -L "$PROJECT_DIR/current" ]]; then
        err "$PROJECT_DIR/current već postoji — projekat je inicijalizovan, koristi 'release'"
    fi
    if [[ -d "$PROJECT_DIR" && -n "$(ls -A "$PROJECT_DIR" 2>/dev/null)" ]]; then
        warn "$PROJECT_DIR postoji i nije prazan — nastavljam (idempotent re-run)"
    fi

    # Port format + opseg + slobodan
    [[ "$PORT" =~ ^[0-9]+$ ]] || err "PORT mora biti numerički"
    if (( PORT < 8000 || PORT > 8999 )); then
        warn "PORT $PORT van očekivanog opsega 8000-8999 (server-conventions sekcija 1.2)"
    fi
    if sudo ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
        err "Port $PORT već je u upotrebi — provjeri 'sudo ss -tlnp | grep :$PORT'"
    fi

    # Required commands
    local missing=()
    for cmd in python3 git nginx certbot dig; do
        command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
    done
    [[ ${#missing[@]} -eq 0 ]] || err "Nedostaje: ${missing[*]}"

    # Sudo bez password-a
    sudo -n true 2>/dev/null || err "sudo NOPASSWD nije konfigurisan za $RUN_USER"

    # Nginx hosts/ folder mora biti includovan u nginx.conf
    [[ -d /etc/nginx/hosts ]] || err "/etc/nginx/hosts ne postoji — provjeri nginx.conf 'include hosts/*.conf'"

    # Systemd unit ne smije postojati za drugi projekat
    if systemctl list-unit-files "$PROJECT_NAME.service" 2>/dev/null | grep -q "$PROJECT_NAME.service"; then
        warn "$PROJECT_NAME.service već postoji u systemd — biće prepisan"
    fi

    # DNS check (warn, ne fail — osim ako SSL je obavezan)
    local resolved
    resolved=$(dig +short "$DOMAIN" A 2>/dev/null | head -1)
    if [[ -z "$resolved" ]]; then
        if [[ "$SKIP_SSL" != "1" ]]; then
            err "DNS za $DOMAIN ne resolvuje — postavi A record ili pokreni sa SKIP_SSL=1"
        else
            warn "DNS za $DOMAIN ne resolvuje, ali SKIP_SSL=1 — nastavljam bez SSL-a"
        fi
    else
        ok "DNS: $DOMAIN → $resolved"
    fi

    ok "Setup pre-checks OK"
}

setup_structure() {
    log "Folder struktura"
    sudo mkdir -p "$PROJECT_DIR"/{releases,shared/var}
    sudo chown -R "$RUN_USER:$RUN_USER" "$PROJECT_DIR"
    ok "$PROJECT_DIR/{releases,shared,shared/var} kreirano"
}

setup_env() {
    log "Setup shared/.env"
    if [[ -f "$SHARED_DIR/.env" ]]; then
        warn "$SHARED_DIR/.env već postoji — preskače se kreiranje"
        chmod 600 "$SHARED_DIR/.env"
        return
    fi

    if [[ -n "${ENV_TEMPLATE:-}" && -f "$ENV_TEMPLATE" ]]; then
        cp "$ENV_TEMPLATE" "$SHARED_DIR/.env"
        chmod 600 "$SHARED_DIR/.env"
        ok ".env iskopiran iz $ENV_TEMPLATE"
        warn "PREGLEDAJ $SHARED_DIR/.env — provjeri da prod vrijednosti nisu staging vrijednosti!"
        warn "(API keys, DB paths, DASHBOARD_API_KEY, ENVIRONMENT=production, itd.)"
        # Pauza za ručni pregled — nastavi tek kad korisnik potvrdi
        if [[ -t 0 ]]; then
            read -rp "Editovan/pregledan .env? Nastavi? [y/N] " ans
            [[ "$ans" == "y" || "$ans" == "Y" ]] || err "Prekinuto — popravi .env i pokreni opet"
        fi
    else
        cat > "$SHARED_DIR/.env" <<EOF
# $PROJECT_NAME — popunjavanje OBAVEZNO prije release-a
# Vidi: docs/operations/server-conventions.md sekcija 2.1 (env vars)
ANTHROPIC_API_KEY=
DASHBOARD_API_KEY=
ENVIRONMENT=production
EOF
        chmod 600 "$SHARED_DIR/.env"
        warn "Prazan .env kreiran u $SHARED_DIR/.env"
        err "Popuni .env pa pokreni opet (skripta je idempotentna — preskočiće već urađene korake)"
    fi
}

setup_systemd() {
    log "Generiši i instaliraj systemd unit"
    local unit="/etc/systemd/system/$PROJECT_NAME.service"

    sudo tee "$unit" >/dev/null <<EOF
[Unit]
Description=$PROJECT_NAME (FastAPI/uvicorn)
After=network.target

[Service]
Type=simple
User=$RUN_USER
Group=$RUN_USER
WorkingDirectory=$PROJECT_DIR/current
EnvironmentFile=$SHARED_DIR/.env
ExecStart=$PROJECT_DIR/current/.venv/bin/uvicorn $ENTRY_POINT --host 127.0.0.1 --port $PORT
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$PROJECT_NAME" >/dev/null 2>&1
    ok "systemd unit instaliran: $unit"
}

setup_systemd_start() {
    log "Start $PROJECT_NAME (prvi put)"
    sudo systemctl start "$PROJECT_NAME"
    sleep 5
    if systemctl is-active --quiet "$PROJECT_NAME"; then
        ok "$PROJECT_NAME active (PID $(systemctl show -p MainPID --value "$PROJECT_NAME"))"
    else
        sudo journalctl -u "$PROJECT_NAME" -n 50 --no-pager
        err "Servis nije aktivan posle start-a — provjeri logove gore"
    fi
}

setup_nginx_http() {
    log "Generiši nginx config (HTTP only — certbot dodaje SSL)"
    local conf="/etc/nginx/hosts/$PROJECT_NAME.conf"

    sudo tee "$conf" >/dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 60s;
    }
}
EOF

    sudo nginx -t || err "nginx config test failed"
    sudo systemctl reload nginx
    ok "nginx HTTP config instaliran i reloadovan: $conf"
}

setup_ssl() {
    if [[ "$SKIP_SSL" == "1" ]]; then
        warn "SSL preskočen (SKIP_SSL=1). Pokreni ručno kad DNS propagira:"
        warn "  sudo certbot --nginx -d $DOMAIN --email $ADMIN_EMAIL --agree-tos --non-interactive --redirect --no-eff-email"
        return
    fi
    log "Issue SSL cert (certbot --nginx)"
    sudo certbot --nginx \
        -d "$DOMAIN" \
        --email "$ADMIN_EMAIL" \
        --agree-tos \
        --non-interactive \
        --redirect \
        --no-eff-email
    ok "SSL cert instaliran za $DOMAIN — nginx automatski reloadovan"
}

setup_health() {
    log "Final health check"
    sleep 2

    if curl -sf "http://127.0.0.1:$PORT/healthz" >/dev/null; then
        ok "/healthz lokalno OK"
    else
        warn "/healthz lokalno FAIL — provjeri 'sudo journalctl -u $PROJECT_NAME -n 50'"
        warn "(Aiasistent gradi index pri prvom startu — može potrajati nekoliko minuta)"
    fi

    if [[ "$SKIP_SSL" != "1" ]]; then
        if curl -sf "https://$DOMAIN/healthz" >/dev/null; then
            ok "/healthz HTTPS OK — https://$DOMAIN/healthz"
        else
            warn "/healthz HTTPS FAIL"
        fi
    else
        if curl -sf "http://$DOMAIN/healthz" >/dev/null; then
            ok "/healthz HTTP OK — http://$DOMAIN/healthz"
        else
            warn "/healthz HTTP FAIL"
        fi
    fi
}

do_setup_domain() {
    log "SETUP-DOMAIN: $PROJECT_NAME → $DOMAIN (port $PORT, branch $BRANCH)"
    setup_pre_checks
    setup_structure
    setup_env

    # Inicijalni release — koristimo iste helpere iz release flow-a.
    # Razlika: pre_checks() (koji traži current symlink) se ne poziva ovdje.
    clone_release
    link_shared
    install_python_deps
    run_migrations
    build_dashboard
    atomic_switch

    setup_systemd
    setup_systemd_start
    setup_nginx_http
    setup_ssl
    setup_health

    echo
    if [[ "$SKIP_SSL" == "1" ]]; then
        ok "SETUP DONE (bez SSL-a) — http://$DOMAIN/healthz"
        warn "Sledeći korak: pokreni certbot ručno kad DNS propagira"
    else
        ok "SETUP DONE — https://$DOMAIN/healthz"
    fi
    ok "Sledeći deploy: 'bash $PROJECT_DIR/current/scripts/deploy.sh release'"
}

# ════════════════════════════════════════════════════════════════
# Main dispatch
# ════════════════════════════════════════════════════════════════

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
    setup-domain)
        do_setup_domain
        ;;
    *)
        sed -n '2,30p' "$0"
        exit 1
        ;;
esac
