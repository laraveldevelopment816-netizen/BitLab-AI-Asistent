# Deploy — BitLab AI Asistent

Server konvencije i opšta logika: [`docs/operations/server-conventions.md`](docs/operations/server-conventions.md).

Ovaj fajl prati **testirane korake** za ovaj konkretan projekat. Svaki korak ima jednu od oznaka:
- `[ ]` — još nije validirano na serveru
- `[x]` — validirano, copy-paste blok ispod radi tačno tako
- `[auto]` — pokriveno u `scripts/deploy.sh`

Server: `ai.bitlab.rs`, user `ai` (sudo). Pattern: A (FastAPI + venv + systemd + symlink).

---

## A) Novi release (postojeći projekat)

**Kada koristiti:** projekat je već inicijalizovan (`current` symlink postoji, systemd radi, `shared/.env` popunjen) i hoćemo da pustimo nove izmjene iz git-a.

### A.0 Varijable (popuniti prije svake sesije)

```bash
export PROJECT_NAME="aiasistent-staging"        # ili aiasistent-prod
export DOMAIN="staging.aiasistent.bitlab.rs"    # ili aiasistent.bitlab.rs
export PORT="8001"                              # iz port mape — staging:8001, prod:8000
export REPO_URL="git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git"
export BRANCH="production-prep"
```

### A.1 Pre-checks `[x]` — validirano 2026-05-05 na `aiasistent-staging`

Cilj: snimiti baseline prije releasea (`current` postoji, app aktivan, port naš, `/healthz` 200).

```bash
echo "=== Struktura ===";          ls -la /home/ai/$PROJECT_NAME/
echo "=== Current release ===";    readlink -f /home/ai/$PROJECT_NAME/current
echo "=== Shared sadržaj ===";     ls -la /home/ai/$PROJECT_NAME/shared/
echo "=== .env ključevi ===";      grep -E '^[A-Z_]+=' /home/ai/$PROJECT_NAME/shared/.env | cut -d= -f1 | sort
echo "=== Service active? ===";    sudo systemctl is-active $PROJECT_NAME
echo "=== Port $PORT ===";         sudo ss -tlnp | grep ":$PORT "
echo "=== Health (lokal) ===";     curl -sf http://127.0.0.1:$PORT/healthz
echo "=== Health (HTTPS) ===";     curl -sf https://$DOMAIN/healthz
echo "=== Nginx config ===";       ls -la /etc/nginx/hosts/$PROJECT_NAME.conf
```

Bug-fix napomena: za `/healthz` koristiti **GET** (ne `curl -I`), inače vraća 405.

### A.1.5 Bootstrap `shared/var/` (samo prvi put kad legacy state je u releaseu) `[x]` — validirano 2026-05-05 na `aiasistent-staging`

> Kontekst: na inicijalno postavljenom staging-u, `products.index.npz` i `products.meta.json` su pravi fajlovi u `data/`, a `var/` (gdje ide SQLite db) ne postoji. Bez ovog koraka, sledeći clean release bi imao prazan `data/` (jer `.gitignore` isključuje index/meta) i app bi ili pala ili rebuildovala index 5min. Ovaj korak je jednokratan po projektu — ne ide u `deploy.sh release` (već eventualno kao `deploy.sh migrate-shared` jednokratna utility-komanda).

```bash
RELEASE_DIR=$(readlink -f /home/ai/$PROJECT_NAME/current)

# 1. Kreiraj shared/var
mkdir -p /home/ai/$PROJECT_NAME/shared/var

# 2. Premjesti generisane fajlove iz aktivnog release-a u shared/var
mv $RELEASE_DIR/data/products.index.npz /home/ai/$PROJECT_NAME/shared/var/
mv $RELEASE_DIR/data/products.meta.json /home/ai/$PROJECT_NAME/shared/var/

# 3. Symlinkuj nazad u data/
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.index.npz $RELEASE_DIR/data/products.index.npz
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.meta.json $RELEASE_DIR/data/products.meta.json

# 4. Symlink var/ → shared/var/ (gdje sjedi SQLite bitlab.db)
ln -sfn /home/ai/$PROJECT_NAME/shared/var $RELEASE_DIR/var

# 5. Permissions
chmod 600 /home/ai/$PROJECT_NAME/shared/.env

# 6. (init_db.py se preskače jer skripta ne postoji u tom legacy releaseu — ide u A.5 iz novog releasea)

# 7. Restart i potvrdi
sudo systemctl restart $PROJECT_NAME
sleep 3
curl -sf http://127.0.0.1:$PORT/healthz | python3 -m json.tool
```

Verifikacija: `products_index_present: true` u `/healthz` odgovoru, bez error-a u `journalctl -u $PROJECT_NAME -n 30`.

### A.2 Clone novog release-a `[x]` — validirano 2026-05-05

```bash
export RELEASE=$(date +%Y%m%d_%H%M)
export RELEASE_DIR=/home/ai/$PROJECT_NAME/releases/$RELEASE

[ -d "$RELEASE_DIR" ] && { echo "❌ Folder već postoji"; return 1; }

cd ~
git clone -b $BRANCH $REPO_URL $RELEASE_DIR
cd $RELEASE_DIR
git log -1 --oneline
```

Pretpostavlja: SSH ključ `ai` user-a ima access na repo (jer je raniji clone radio).

### A.3 Symlink shared resources `[x]` — validirano 2026-05-05

```bash
ln -sfn /home/ai/$PROJECT_NAME/shared/.env $RELEASE_DIR/.env
ln -sfn /home/ai/$PROJECT_NAME/shared/var $RELEASE_DIR/var
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.index.npz $RELEASE_DIR/data/products.index.npz
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.meta.json $RELEASE_DIR/data/products.meta.json
```

App traži index/meta u `data/` (po `app/config.py`), pa simlinkovi idu tamo iako su fajlovi fizički u `shared/var/`. SQLite `bitlab.db` se kreira pod `var/` u app pokretanju (zahvaljujući `var → shared/var` symlinku, fajl završava u shared).

### A.4 Python venv + deps `[x]` — validirano 2026-05-05

Najduži korak (~2-3 min, `.venv` ~860MB).

```bash
cd $RELEASE_DIR
python3 -m venv .venv
.venv/bin/pip install --upgrade pip wheel
.venv/bin/pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
```

Verifikacija:

```bash
.venv/bin/python -c "import torch; print('cuda:', torch.cuda.is_available())"  # False
.venv/bin/python -c "from app.config import settings; print('chat:', settings.chat_model)"  # claude-sonnet-4-6
```

Ako `chat_model` nije `claude-sonnet-4-6`, znači branch ne sadrži commit `069b691`. Provjeri `git log -1` u releaseu.

### A.5 Migracije (idempotentne) `[x]` — validirano 2026-05-05

```bash
cd $RELEASE_DIR
.venv/bin/python scripts/init_db.py            # kreira requests, tool_calls (sa session_id)
.venv/bin/python scripts/migrate_session_id.py # no-op ako kolona postoji
.venv/bin/python scripts/build_categories.py   # regen data/categories.json iz products.meta
```

DB se piše na `shared/var/bitlab.db` zahvaljujući `var → shared/var` simlinkku iz A.3. `sqlite3` CLI nije instaliran na serveru — verifikacija je preko `migrate_session_id.py` (kaže "kolona već postoji" ako je schema OK).

### A.6 Dashboard build (Vite SPA) `[x]` — validirano 2026-05-05

```bash
cd $RELEASE_DIR/dashboard
pnpm install --frozen-lockfile
pnpm build
[ -f dist/index.html ] && echo "✅ build OK"
```

Prerequisite: `pnpm` na serveru (corepack ili `npm i -g`). Build je brz (~1-2s pošto su deps cached u node_modules).

**Otvoreno (TODO posle prvog release-a):** dashboard `/admin/` nije servisiran na staging-u. Nginx config `aiasistent-staging.conf` nema `/admin/` location, a `app/main.py` ne mounta `dashboard/dist/`. Dist se gradi i sjedi u releaseu, ali nije accessible. Treba ili nginx alias na `dist/` ili FastAPI mount.

### A.7 Atomic symlink switch `[x]` — validirano 2026-05-05

```bash
ln -sfn $RELEASE_DIR /home/ai/$PROJECT_NAME/current
readlink -f /home/ai/$PROJECT_NAME/current   # mora biti $RELEASE_DIR
```

`ln -sfn` je atomski rename (`-n` = no-dereference) — nikad nema "split-brain" stanja. Servis još uvijek izvršava stari proces dok se ne uradi A.8.

### A.8 Restart systemd servisa `[x]` — validirano 2026-05-05

```bash
sudo systemctl restart $PROJECT_NAME
sleep 5
sudo systemctl is-active $PROJECT_NAME              # → active
sudo systemctl status $PROJECT_NAME --no-pager | grep "Main PID"   # novi PID
```

`systemd` unit ima `WorkingDirectory=/home/ai/$PROJECT_NAME/current`, pa nakon switch-a + restart-a, uvicorn učitava kod iz novog releasea.

### A.9 Health check (golden test) `[x]` — validirano 2026-05-05

```bash
# /healthz preko HTTPS
curl -sf https://$DOMAIN/healthz

# Golden assertions
RESP=$(curl -sf https://$DOMAIN/healthz)
echo "$RESP" | grep -q "claude-sonnet-4-6" && echo "✅ chat_model OK"
echo "$RESP" | grep -q 'products_index_present":true' && echo "✅ index"
echo "$RESP" | grep -q 'faq_present":true' && echo "✅ faq"

# Dashboard stats endpoint (DB + auth)
DASHBOARD_API_KEY=$(grep ^DASHBOARD_API_KEY /home/ai/$PROJECT_NAME/shared/.env | cut -d= -f2)
curl -sf -H "Authorization: Bearer $DASHBOARD_API_KEY" http://127.0.0.1:$PORT/api/dashboard/stats

# Bez error-a u logu
sudo journalctl -u $PROJECT_NAME -n 30 --no-pager | grep -iE 'error|fail|traceback' || echo "✅ clean log"
```

Glavni signal: `chat_model` u `/healthz` mora biti vrijednost iz `app/config.py` na branchu novog release-a, ne stari. Ako se ne mijenja → restart nije pokupio novi kod.

### A.10 Cleanup starih release-ova `[x]` — validirano 2026-05-05

```bash
ls -t /home/ai/$PROJECT_NAME/releases/ | tail -n +6 | \
  xargs -r -I{} rm -rf /home/ai/$PROJECT_NAME/releases/{}
```

`xargs -r` je no-op kad je input prazan (manje od 5 release-ova). KEEP broj je konfigurabilan kroz `KEEP_RELEASES` env u skripti.

---

## B) Početni setup za novi domen

**Kada koristiti:** kreće potpuno nov projekat na novom poddomenu (npr. `playwright-router.bitlab.rs`). Folder `/home/ai/<projekat>` ne postoji ili je prazan.

### B.0 Varijable

```bash
export PROJECT_NAME="<projekat>"                # folder pod /home/ai/
export DOMAIN="<poddomen.bitlab.rs>"
export PORT="<iz port mape, sekcija 1.2 server-conventions>"
export REPO_URL="<git@...>"
export BRANCH="main"
export ENTRY_POINT="app.main:app"
export ADMIN_EMAIL="admin@bitlab.rs"
```

### B.1 Pre-checks (port, DNS, folder) `[ ]`

```bash
# TODO: validirati
```

### B.2 Inicijalna struktura `[ ]`

```bash
# TODO: validirati
```

### B.3 Popuni shared/.env `[ ]`

```bash
# TODO: validirati
```

### B.4 Inicijalni release (clone + build) `[ ]`

```bash
# TODO: validirati — naslanja se na A.2–A.6
```

### B.5 Atomic switch `[ ]`

```bash
# TODO: validirati — isto kao A.7
```

### B.6 Systemd unit `[ ]`

```bash
# TODO: validirati
```

### B.7 Nginx config (HTTP) `[ ]`

```bash
# TODO: validirati
```

### B.8 SSL (certbot) `[ ]`

```bash
# TODO: validirati
```

### B.9 Health checks (HTTP/HTTPS) `[ ]`

```bash
# TODO: validirati
```

---

## Rollback

```bash
PROJECT_NAME="aiasistent-prod"
PREV=$(ls -t /home/ai/$PROJECT_NAME/releases | sed -n 2p)
ln -sfn /home/ai/$PROJECT_NAME/releases/$PREV /home/ai/$PROJECT_NAME/current
sudo systemctl restart $PROJECT_NAME
sudo systemctl status $PROJECT_NAME --no-pager
```

---

## Skripta `scripts/deploy.sh`

| Komanda                  | Pokriva     | Status |
|--------------------------|-------------|--------|
| `deploy.sh release`      | A.2 → A.10  | `[auto]` end-to-end test 2026-05-05 — release `20260505_1526` na staging-u prošao u jednom pozivu (~3 min) |
| `deploy.sh rollback`     | Rollback    | `[auto]` logika napisana — end-to-end test: TODO |
| `deploy.sh setup-domain` | B.1 → B.9   | `[ ]` Faza B |

### Kako koristiti — `release`

Skripta čita pet env varijabli. Najlakše je da svaki projekat ima svoj env helper fajl u `~/`:

```bash
# /home/ai/aiasistent-staging.env
export PROJECT_NAME="aiasistent-staging"
export DOMAIN="staging.aiasistent.bitlab.rs"
export PORT="8001"
export REPO_URL="git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git"
export BRANCH="production-prep"
```

Onda za novi release:

```bash
source ~/aiasistent-staging.env
bash /home/ai/$PROJECT_NAME/current/scripts/deploy.sh release
```

Skripta:
1. Pre-checks (`current` symlink, `shared/.env`, `shared/var/`)
2. Clone novog release-a (`releases/$(date +%Y%m%d_%H%M)`)
3. Symlinkuje `.env`, `var/`, `data/products.{index,meta}` na `shared/var/`
4. `python3 -m venv .venv` + `pip install -e . --extra-index-url ... cpu`
5. `init_db.py` + `migrate_session_id.py` + `build_categories.py`
6. `pnpm install --frozen-lockfile && pnpm build`
7. `ln -sfn $RELEASE_DIR current` (atomic switch)
8. `sudo systemctl restart $PROJECT_NAME`
9. Health check (`/healthz` lokalno + HTTPS, dashboard stats sa auth, error scan u logu)
10. Briše release-ove starije od 5 (konfigurabilno: `KEEP_RELEASES=N`)

`set -euo pipefail` na vrhu — na bilo kojoj grešci skripta staje. Failed release ostaje u `releases/` (može se ručno obrisati ili će sledeći cleanup pokupiti), `current` ostaje na prethodnom releaseu jer atomic switch (korak 7) dolazi tek nakon što sve u prethodnih 6 koraka prođe.

### Kako koristiti — `rollback`

```bash
source ~/aiasistent-staging.env
bash /home/ai/$PROJECT_NAME/current/scripts/deploy.sh rollback
```

Switch-uje `current` na release **odmah ispod** trenutnog (po datumu) i restartuje servis. Brzo (<10s downtime — koliko traje `systemctl restart`).

### Prerekviziti

Server `ai.bitlab.rs` već ima:
- Python 3.11+ (testirano sa 3.13.5)
- Node 22 + corepack pnpm@10
- systemd unit `$PROJECT_NAME.service` (kreiran u Fazi B)
- nginx host config u `/etc/nginx/hosts/$PROJECT_NAME.conf`
- `ai` user u `sudoers` (skripta poziva `sudo systemctl restart`)
- SSH ključ `ai` user-a dodat kao deploy key u GitHub repo
