# Manual setup-domain — 14 koraka

`bash ~/deploy.sh setup-domain` razbijen na 14 funkcija. Pozivaj jednu po jednu, testiraj output, pa nastavljaj.

## Priprema

NOPASSWD (jednom zauvijek za ai user-a):

```
sudo visudo -f /etc/sudoers.d/ai
```

Dodaj liniju, snimi (Ctrl+O, Enter, Ctrl+X):

```
ai ALL=(ALL) NOPASSWD: ALL
```

Po SSH sesiji — PATH + env + lib + err override:

```
export PATH="/usr/sbin:$PATH"
```

```
source ~/aiasistent-prod.env
```

```
source <(sed -e '/^set -euo pipefail$/d' -e '/^case /,/^esac$/d' ~/deploy.sh)
```

```
err() { printf '\e[1;31m✗ %s\e[0m\n' "$*" >&2; return 1; }
```

Verifikacija:

```
echo "$PROJECT_NAME / $DOMAIN / $PORT / $BRANCH"
```

```
which nginx
```

Mora dati `/usr/sbin/nginx`.

---

## Korak 1 — `setup_pre_checks`

Provjerava: required env (ENTRY_POINT, ADMIN_EMAIL), `current` symlink ne postoji, port slobodan, required komande (python3, git, nginx, certbot, dig), sudo NOPASSWD, `/etc/nginx/hosts/`, DNS resolves.

```
setup_pre_checks
```

**Verifikacija:** zadnji red `✓ Setup pre-checks OK`. Ako pukne — popravi (npr. instaliraj nedostajući paket) pa pokreni ponovo.

---

## Korak 2 — `setup_structure`

`sudo mkdir -p ~/aiasistent-prod/{releases,shared/var}` + chown.

```
setup_structure
```

**Verifikacija:**

```
ls -la ~/aiasistent-prod/
```

Treba vidjeti `releases/` i `shared/`.

---

## Korak 3 — `setup_env`

Kopira `$ENV_TEMPLATE` (`/home/ai/aiasistent-staging/shared/.env`) u `~/aiasistent-prod/shared/.env` sa chmod 600.

**🛑 PAUZIRA** sa `read -p "Editovan/pregledan .env? Nastavi? [y/N]"`.

```
setup_env
```

**Kad pauzira — otvori drugi SSH tab** i edituj prod env:

```
nano ~/aiasistent-prod/shared/.env
```

Provjeri/promijeni: `ENVIRONMENT=production`, `DASHBOARD_API_KEY` (novi za prod, npr. `openssl rand -hex 32`), bilo šta sa `staging` u URL-u/imenu.

Vrati se u prvi tab → pritisni `y`.

---

## Korak 4 — `clone_release`

`RELEASE=$(date +%Y%m%d_%H%M)` → `git clone -b main` u `releases/$RELEASE`. Setuje globalne `RELEASE` i `RELEASE_DIR`.

```
clone_release
```

**Verifikacija:**

```
echo "$RELEASE / $RELEASE_DIR"
ls "$RELEASE_DIR" | head
```

Mora postojati `app/`, `pyproject.toml` itd.

---

## Korak 5 — `link_shared`

Symlinkuje `shared/.env` → `release/.env`, `shared/var` → `release/var`. Ako `release/data/` postoji, dodaje `products.index.npz` i `products.meta.json` simlinkove.

```
link_shared
```

**Verifikacija:**

```
ls -la "$RELEASE_DIR/.env" "$RELEASE_DIR/var"
```

Treba `lrwxrwxrwx ... -> /home/ai/aiasistent-prod/shared/...`.

---

## Korak 6 — `install_python_deps`

`python3 -m venv .venv` + `pip install -e . --extra-index-url cpu-torch`. **~3-5 min** prvi put.

```
install_python_deps
```

**Verifikacija:**

```
"$RELEASE_DIR/.venv/bin/python" --version
"$RELEASE_DIR/.venv/bin/pip" list | head
```

---

## Korak 7 — `run_migrations`

Pokreće idempotente skripte ako postoje: `init_db.py`, `migrate_session_id.py`, `build_categories.py`. Skipuje ako nema.

```
run_migrations
```

**Verifikacija:** zadnji red `✓ Migracije done`. Ako neka pukne, vidiš python traceback.

---

## Korak 8 — `build_dashboard`

Ako `release/dashboard/` postoji: `pnpm install && pnpm build`, pa `sed` za `__BITLAB_DASHBOARD_KEY_PLACEHOLDER__` → vrijednost iz `shared/.env`.

```
build_dashboard
```

**Verifikacija:**

```
ls "$RELEASE_DIR/dashboard/dist/index.html" 2>/dev/null && echo "build OK"
```

---

## Korak 9 — `atomic_switch`

`ln -sfn $RELEASE_DIR ~/aiasistent-prod/current`.

```
atomic_switch
```

**Verifikacija:**

```
readlink -f ~/aiasistent-prod/current
```

Mora pokazati `releases/<TS>`.

---

## Korak 10 — `setup_systemd`

Generiše `/etc/systemd/system/aiasistent-prod.service` (Type=simple, uvicorn, EnvironmentFile=shared/.env), `daemon-reload`, `enable`.

```
setup_systemd
```

**Verifikacija:**

```
systemctl cat aiasistent-prod | head -20
```

---

## Korak 11 — `setup_systemd_start`

`sudo systemctl start aiasistent-prod` + sleep 5 + active check.

```
setup_systemd_start
```

**Ako pukne**, skripta sama dump-uje `journalctl -u aiasistent-prod -n 50`. Najčešći razlog: greška u `.env` ili nedostaje neki dep. Popravi → ponovi.

---

## Korak 12 — `setup_nginx_http`

Generiše `/etc/nginx/hosts/aiasistent-prod.conf` sa `listen 80; server_name $DOMAIN; location / { proxy_pass http://127.0.0.1:$PORT; }`. `nginx -t && reload`.

```
setup_nginx_http
```

**Verifikacija:**

```
cat /etc/nginx/hosts/aiasistent-prod.conf
curl -I http://aiasistent.bitlab.rs/
```

Drugi treba dati `200 OK` (kroz nginx → uvicorn).

---

## Korak 13 — `setup_ssl`

`certbot --nginx -d $DOMAIN --email $ADMIN_EMAIL --redirect`. Edituje nginx config (dodaje 443 + redirect). **Preskače ako `$SKIP_SSL=1`.**

```
setup_ssl
```

**Verifikacija:**

```
sudo ls /etc/letsencrypt/live/aiasistent.bitlab.rs/
curl -I https://aiasistent.bitlab.rs/
```

---

## Korak 14 — `setup_health`

Curl-uje `/healthz` lokalno (`127.0.0.1:8000`) i kroz HTTPS (`https://aiasistent.bitlab.rs`). Warning ako `/healthz` ne postoji ili 4xx/5xx.

```
setup_health
```

**Verifikacija:**

```
curl https://aiasistent.bitlab.rs/healthz
```

---

## Gotovo

Ako je sve prošlo: `aiasistent.bitlab.rs` je live. Sledeći release ide kroz `bash ~/deploy.sh release` (ne `setup-domain`).

## Recovery shortcuts

- **Servis ne radi:** `sudo journalctl -u aiasistent-prod -n 50 --no-pager`
- **nginx greška:** `sudo nginx -t` (test config), `sudo tail /var/log/nginx/error.log`
- **Cert problem:** `sudo certbot certificates`
- **Sve sruši:** RUNBOOK-1 ima rollback sekciju (delete systemd, nginx config, cert, project folder)
