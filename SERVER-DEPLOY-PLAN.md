# Server deploy plan — BitLab AI Asistent

> **Za koga:** Claude Code instanca instalirana **na serveru** `ai.bitlab.rs`.
> **Master server konvencije:** [`DEPLOY_GUIDE.md`](./DEPLOY_GUIDE.md)
> (Pattern A — single FastAPI, symlink releases, `/home/ai/`,
> `/etc/nginx/hosts/`). **Ne kopiraj** taj guide — referenciraj ga.
> **Ovaj fajl** sadrži samo BitLab-specifične korake i odluke koje
> generic Pattern A guide ne pokriva.
>
> **Trenutni branch:** `production-prep` (PR otvoren prema `main`).
> Posle uspješnog server-side smoke testa: merge na `main`.

---

## 0. TLDR — šta server-side Claude radi

1. **Pročita `DEPLOY_GUIDE.md` Sekcije 0–2** za server kontekst
2. **Pročita ovaj fajl u cjelini** za projekat-specifične korake
3. **Krene sa STAGING** (`staging.aiasistent.bitlab.rs`, port 8001)
4. Test → manualni QA sa Ivanom → tek onda **PROD migracija** (port 8000)
5. Stari legacy `aiasistent-prod` se backup-uje, novi symlink pattern preuzima

---

## 1. Specifične varijable za naš projekat

### 1.1 STAGING (idi prvo)

```bash
export PROJECT_NAME="aiasistent-staging"
export DOMAIN="staging.aiasistent.bitlab.rs"
export PORT="8001"                                              # iz port mape
export REPO_URL="git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git"
export BRANCH="production-prep"                                  # NE main — još nije merge-ovan
export ENTRY_POINT="app.main:app"
export ADMIN_EMAIL="bjovkovic@gmail.com"
```

### 1.2 PROD (tek nakon zelenog staging-a)

```bash
export PROJECT_NAME="aiasistent-prod"
export DOMAIN="aiasistent.bitlab.rs"
export PORT="8000"
export REPO_URL="git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git"
export BRANCH="main"                                             # tek nakon PR merge-a
export ENTRY_POINT="app.main:app"
export ADMIN_EMAIL="bjovkovic@gmail.com"
```

> ⚠️ Postojeći `aiasistent-prod` na portu 8000 je **legacy bez symlink pattern-a**.
> Vidi Sekciju 6 (Migracija legacy → symlink) za bezbjednu zamjenu.

---

## 2. Šta je drugačije od generic Pattern A

| Stavka | Generic Pattern A | Naš slučaj |
|---|---|---|
| Sistem deps | nginx, certbot, python | + **node 20+ i pnpm** za dashboard build |
| Repo install | `pip install -r requirements.txt` | `pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu` (CPU torch ~200MB) |
| Statički fajlovi | App ih servira | **Dashboard SPA** (`dashboard/dist/`) servira nginx pod `/admin/` |
| Veliki gitignore artifacts | — | `data/products.index.npz` (7.2MB) i `data/products.meta.json` (5.1MB) — generišu se **na serveru** prvi put (~5min CPU) |
| DB | često Postgres | **SQLite** u `shared/var/bitlab.db` (perzistira između releaseva) |
| Health endpoint | `/health` | **`/healthz`** (mala razlika, lako se zaboravi) |
| Lifespan task | — | **Lazy load** sentence-transformers (~30-50s prvi `/api/chat`) |

---

## 3. Pre-deploy checklist

```bash
# 3.1 Server context
hostname                                  # ai.bitlab.rs
whoami                                    # ai
sudo -n true && echo "✅ sudo bez lozinke" || echo "⚠️ sudo traži lozinku"

# 3.2 Već instaliran software
nginx -v                                  # treba >= 1.18
certbot --version                         # treba >= 1.x
python3 --version                         # treba >= 3.11
git --version

# 3.3 Node + pnpm (možda nije instaliran — generic guide ne pominje)
node --version 2>/dev/null || echo "⚠️ Node nije instaliran"
pnpm --version 2>/dev/null || echo "⚠️ pnpm nije instaliran"

# Ako fali, instaliraj:
# curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
# sudo apt-get install -y nodejs
# sudo npm i -g pnpm

# 3.4 Port slobodan (samo za STAGING; prod 8000 je trenutno zauzet legacy-jem)
sudo ss -tlnp | grep ":$PORT " && echo "❌ PORT zauzet" || echo "✅ PORT slobodan"

# 3.5 DNS resolva na ovaj server
SERVER_IP=$(curl -s ifconfig.me)
DNS_IP=$(dig +short $DOMAIN | tail -1)
[ "$SERVER_IP" = "$DNS_IP" ] && echo "✅ DNS OK" || echo "❌ DNS pokazuje na $DNS_IP, server je $SERVER_IP"

# 3.6 Provjera da li imamo sve API ključeve (Ivan ih daje out-of-band)
echo "Treba u shared/.env: ANTHROPIC_API_KEY, DASHBOARD_API_KEY, AZURE_SPEECH_KEY (opcionalno), GROQ_API_KEY (opcionalno)"
```

---

## 4. Inicijalna struktura — naša specifičnost

```bash
# Standardno (DEPLOY_GUIDE A.3)
mkdir -p /home/ai/$PROJECT_NAME/{releases,shared/logs}

# DODAJ za nas: var/ za SQLite DB (preživi releaseve)
mkdir -p /home/ai/$PROJECT_NAME/shared/var

# DODAJ: cache za sentence-transformers model (~120MB) da ne skida pri svakom releasu
mkdir -p /home/ai/$PROJECT_NAME/shared/hf-cache

# Tajne
touch /home/ai/$PROJECT_NAME/shared/.env
chmod 600 /home/ai/$PROJECT_NAME/shared/.env
```

---

## 5. Sadržaj `shared/.env`

Pitaj Ivana za prave vrijednosti (out-of-band, NE u git-u). Template:

```env
# ── OBAVEZNO ────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-api03-...

# Generiši: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
DASHBOARD_API_KEY=eCVylDhsSbMeivD2xe6g-XZg605WsVRSXko0dHHA23I

# ── Modeli (mogu se override) ──────────────────────────────
# Sesija 8: Sonnet 4.6 default za chat (Haiku izbačen — vidi README "Modelska odluka")
# CHAT_MODEL=claude-sonnet-4-6
# EMAIL_MODEL=claude-sonnet-4-6

# ── TTS / STT (preporučeno za demo kvalitet) ───────────────
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=westeurope
AZURE_STT_LANGUAGE=hr-HR
TTS_VOICE=hr-HR-GabrijelaNeural

GROQ_API_KEY=

# ── Webshop ───────────────────────────────────────────────
WEBSHOP_BASE_URL=https://webshop.bitlab.rs
PRODUCT_URL_TEMPLATE=https://webshop.bitlab.rs/proizvod/{urlhash}

# ── CORS — staging i prod su odvojeni ─────────────────────
# Za STAGING:
# ALLOWED_ORIGINS=["https://staging.aiasistent.bitlab.rs","https://webshop.bitlab.rs"]
# Za PROD:
# ALLOWED_ORIGINS=["https://aiasistent.bitlab.rs","https://webshop.bitlab.rs"]

# ── Dashboard storage (default radi, override samo ako migriraš) ──
# DASHBOARD_DB_URL=sqlite+aiosqlite:////home/ai/aiasistent-staging/shared/var/bitlab.db

# ── HuggingFace cache (sprečava re-download modela) ──────
HF_HOME=/home/ai/aiasistent-staging/shared/hf-cache
SENTENCE_TRANSFORMERS_HOME=/home/ai/aiasistent-staging/shared/hf-cache
```

---

## 6. Inicijalni release — koraci specifični za nas

```bash
RELEASE=$(date +%Y%m%d_%H%M)
RELEASE_DIR=/home/ai/$PROJECT_NAME/releases/$RELEASE
echo "📦 Release: $RELEASE"

# 6.1 Clone
git clone -b $BRANCH $REPO_URL $RELEASE_DIR
cd $RELEASE_DIR

# 6.2 Symlinks za shared resources
ln -sfn /home/ai/$PROJECT_NAME/shared/.env $RELEASE_DIR/.env
ln -sfn /home/ai/$PROJECT_NAME/shared/var  $RELEASE_DIR/var

# 6.3 Python venv + deps (CPU torch je obavezan flag)
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu

# 6.4 Generiši product index (samo prvi put ili kad se katalog promijeni)
# Trajanje: ~5 min, ~5GB temp diska
if [ ! -f /home/ai/$PROJECT_NAME/shared/var/products.index.npz ]; then
    echo "🔨 Generišem product index (jednokratno, ~5min)..."
    python scripts/embed_products.py
    # Premjesti u shared/var da preživi releaseve
    mv data/products.index.npz /home/ai/$PROJECT_NAME/shared/var/
    mv data/products.meta.json /home/ai/$PROJECT_NAME/shared/var/
fi
# Symlink iz release-a → shared
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.index.npz data/products.index.npz
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.meta.json data/products.meta.json

# 6.5 Generiši kategorije i missing image audit (deterministički)
python scripts/build_categories.py
python scripts/audit_missing_images.py --concurrency 50  # ~2-3 min

# 6.6 Init dashboard DB schema (idempotentno)
python scripts/init_db.py

# 6.7 Build dashboard SPA
cd dashboard
pnpm install --frozen-lockfile
pnpm build           # → dashboard/dist/
cd ..

# 6.8 Quick smoke prije atomic switch
.venv/bin/python -c "from app.main import app; print('✅ Import OK')"

# 6.9 Atomic switch
ln -sfn $RELEASE_DIR /home/ai/$PROJECT_NAME/current
readlink -f /home/ai/$PROJECT_NAME/current   # verifikuj
```

---

## 7. Systemd unit — naša specifičnost

Razlika od generic A.6:
- `--workers 2` (FastAPI sa lazy load ima ~600MB RAM po worker-u, na 2GB VPS-u 2 je optimum)
- Memory limit + tasks limit (sentence-transformers je memory-hungry)
- Ne pravimo health endpoint kontrolu kroz systemd jer prvi `/api/chat` traje 30-50s zbog model load-a (lažni "unhealthy")

```bash
sudo tee /etc/systemd/system/$PROJECT_NAME.service > /dev/null <<EOF
[Unit]
Description=BitLab AI Asistent ($PROJECT_NAME, $DOMAIN, port $PORT)
After=network.target

[Service]
Type=simple
User=ai
Group=ai
WorkingDirectory=/home/ai/$PROJECT_NAME/current
EnvironmentFile=/home/ai/$PROJECT_NAME/current/.env
ExecStart=/home/ai/$PROJECT_NAME/current/.venv/bin/uvicorn $ENTRY_POINT \\
    --host 127.0.0.1 --port $PORT --workers 2 \\
    --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=5

# Resource limits (sentence-transformers + faster-whisper drže ~600MB / worker)
MemoryMax=1500M
TasksMax=300

StandardOutput=journal
StandardError=journal
SyslogIdentifier=$PROJECT_NAME

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now $PROJECT_NAME

# Sačekaj 5-10s — uvicorn startup, ali NE prvi /api/chat
sleep 8
sudo systemctl status $PROJECT_NAME --no-pager
sudo journalctl -u $PROJECT_NAME -n 30 --no-pager

# Health (NE /health, naš endpoint je /healthz)
curl -sf http://127.0.0.1:$PORT/healthz | head -c 200 || echo "⚠️ healthz ne odgovara"
```

---

## 8. Nginx config — naša specifičnost

Razlike od generic A.7:
- `/admin/` location servira **dashboard SPA static** iz `current/dashboard/dist/`
- `/api/dashboard/` proxy na port + Bearer auth (već u app)
- `/api/` opšti proxy
- `/public/` proxy (FastAPI servira widget.js)
- `client_max_body_size 30M` (STT audio može do 25MB)

```bash
sudo tee /etc/nginx/hosts/$PROJECT_NAME.conf > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 30M;
    client_body_timeout 60s;

    # Dashboard SPA (static, iz current symlink-a — auto follow na novi release)
    location /admin/ {
        alias /home/ai/$PROJECT_NAME/current/dashboard/dist/;
        try_files \$uri \$uri/ /admin/index.html;

        # Long cache za hashed Vite assets
        location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)\$ {
            alias /home/ai/$PROJECT_NAME/current/dashboard/dist/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API + healthz (sve ide na uvicorn)
    location /api/ {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;       # chat može trajati zbog tool calls
        proxy_send_timeout 120s;
        proxy_buffering off;            # za buduće streaming
    }

    location = /healthz {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        access_log off;
    }

    # Widget.js + voice.html — FastAPI servira public/
    location /public/ {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        expires 1h;
    }

    # Root: widget demo (FastAPI servira public/widget.html)
    location = / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
    }

    location = /docs {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
    }

    access_log /home/ai/$PROJECT_NAME/shared/logs/nginx-access.log;
    error_log  /home/ai/$PROJECT_NAME/shared/logs/nginx-error.log warn;
}
EOF

sudo nginx -t || { echo "❌ Nginx config invalid"; exit 1; }
sudo systemctl reload nginx
curl -I http://$DOMAIN
```

Onda SSL (standardno, vidi `DEPLOY_GUIDE.md` A.8):

```bash
sudo certbot --nginx -d $DOMAIN \
    --non-interactive --agree-tos --email $ADMIN_EMAIL --redirect

curl -I https://$DOMAIN
sudo certbot renew --dry-run
```

---

## 9. Smoke test scenariji (post-deploy QA)

```bash
KEY=$(grep ^DASHBOARD_API_KEY /home/ai/$PROJECT_NAME/shared/.env | cut -d= -f2)

# 9.1 Healthz
curl -fsS https://$DOMAIN/healthz | jq

# 9.2 Chat — kategorija filter (Sesija 1 + 8)
curl -sX POST https://$DOMAIN/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"imate li gaming mis","channel":"chat"}' | jq -r '.reply' | head -c 300

# 9.3 Chat — out-of-catalog (Sesija 8 hotfix custom build poziv)
curl -sX POST https://$DOMAIN/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"trebam gaming desktop PC do 1500 KM","channel":"chat"}' \
    | jq -r '.reply' | grep -i "sklop\|konfigura\|izać\|tim" \
    && echo "✅ Custom build poziv prisutan" || echo "❌ FALIO custom build hotfix"

# 9.4 Chat — typo (Sesija 8 hotfix)
curl -sX POST https://$DOMAIN/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"Imate li lapatovoe","channel":"chat"}' \
    | jq -r '.reply' | grep -iv "nemamo laptop" \
    && echo "✅ Typo handled" || echo "❌ Typo halucinacija"

# 9.5 Dashboard auth
curl -sf -o /dev/null -w "%{http_code}\n" https://$DOMAIN/api/dashboard/requests
# Očekivano: 401

curl -sf https://$DOMAIN/api/dashboard/requests -H "Authorization: Bearer $KEY" | jq '.total'
# Očekivano: integer

# 9.6 Compare endpoint
curl -sX POST https://$DOMAIN/api/dashboard/compare \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -d '{"message":"imate li tastaturu","channel":"chat","models":["haiku","sonnet"]}' \
    | jq '.results[] | {model_key, status, latency_ms}'

# 9.7 Dashboard SPA učita
curl -sI https://$DOMAIN/admin/ | head -3
# Očekivano: 200, content-type: text/html

# 9.8 Voice TTS (Sesija 8 hotfix cijene)
curl -sX POST https://$DOMAIN/api/tts \
    -H "Content-Type: application/json" \
    -d '{"text":"Cijena je 1.936 KM"}' --output /tmp/test.mp3
ls -lh /tmp/test.mp3   # > 0 bytes = TTS radi
```

---

## 10. Migracija legacy `aiasistent-prod` → symlink pattern

> Treba kad staging zazeleni i Ivan odobri prelazak na prod.

### Plan
1. **Backup** legacy direktorijuma + db
2. **Stop** legacy systemd unit (ako postoji)
3. **Pripremi novi** symlink pattern u `/home/ai/aiasistent-prod/` (port ostaje 8000)
4. **Migriraj postojeći `var/bitlab.db`** ako postoji u legacy lokaciji (ne gubi history)
5. **Zamijeni nginx config** za `aiasistent.bitlab.rs`
6. **Start** novi systemd unit
7. **Smoke test**
8. **Backup za rollback** sačuvaj 7+ dana

### Koraci

```bash
# 10.1 Snimi gdje legacy živi
LEGACY_DIR=$(systemctl show aiasistent-prod -p WorkingDirectory --value 2>/dev/null || echo "")
echo "Legacy dir: $LEGACY_DIR"
sudo systemctl status aiasistent-prod --no-pager 2>&1 | head -10

# 10.2 Backup
BACKUP_DIR=/home/ai/_backups/aiasistent-prod-$(date +%Y%m%d_%H%M)
mkdir -p $BACKUP_DIR
[ -n "$LEGACY_DIR" ] && [ -d "$LEGACY_DIR" ] && sudo cp -a "$LEGACY_DIR" $BACKUP_DIR/
sudo cp /etc/nginx/hosts/aiasistent*.conf $BACKUP_DIR/ 2>/dev/null
sudo cp /etc/systemd/system/aiasistent-prod*.service $BACKUP_DIR/ 2>/dev/null
echo "✅ Backup u $BACKUP_DIR"

# 10.3 Stop legacy (NE disable još, da možemo lako rollback)
sudo systemctl stop aiasistent-prod 2>/dev/null || echo "ℹ️ Nema aiasistent-prod servisa"

# 10.4 Pripremi novi pattern (Sekcija 4-8 ovog plana, ali sa PROD vars iz 1.2)
# ... pokreni Sekciju 4-8 sa PROJECT_NAME=aiasistent-prod, PORT=8000, BRANCH=main

# 10.5 Migriraj DB ako legacy ima
LEGACY_DB="$LEGACY_DIR/var/bitlab.db"
[ -f "$LEGACY_DB" ] && cp "$LEGACY_DB" /home/ai/aiasistent-prod/shared/var/bitlab.db && echo "✅ DB migrirana"

# 10.6 Disable legacy unit (poslije zelenog smoke testa)
sudo systemctl disable aiasistent-prod
# (servis je već stopiran u 10.3)

# 10.7 Smoke test sve scenarije iz Sekcije 9
```

### Rollback ako prod migracija pukne

```bash
# Vrati legacy iz backup-a
sudo systemctl stop aiasistent-prod                # zaustavi novi
sudo cp $BACKUP_DIR/aiasistent-prod*.service /etc/systemd/system/ 2>/dev/null
sudo cp $BACKUP_DIR/aiasistent*.conf /etc/nginx/hosts/
sudo systemctl daemon-reload
sudo systemctl start aiasistent-prod
sudo systemctl reload nginx
```

---

## 11. Re-deploy (svaka sledeća iteracija)

Standardno (DEPLOY_GUIDE A.9), uz dvije naše dodatne tačke:

```bash
RELEASE=$(date +%Y%m%d_%H%M)
RELEASE_DIR=/home/ai/$PROJECT_NAME/releases/$RELEASE

git clone -b $BRANCH $REPO_URL $RELEASE_DIR
cd $RELEASE_DIR

# Symlinks (env, var, hf-cache pokriva venv path traversal automatski)
ln -sfn /home/ai/$PROJECT_NAME/shared/.env $RELEASE_DIR/.env
ln -sfn /home/ai/$PROJECT_NAME/shared/var  $RELEASE_DIR/var
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.index.npz data/products.index.npz
ln -sfn /home/ai/$PROJECT_NAME/shared/var/products.meta.json data/products.meta.json

# Build Python deps
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu

# DODATNO: regeneriši kategorije + audit (deterministički, brzo)
python scripts/build_categories.py
python scripts/audit_missing_images.py --concurrency 50 || echo "⚠️ audit pao, nastavi"

# DODATNO: dashboard rebuild
cd dashboard && pnpm install --frozen-lockfile && pnpm build && cd ..

# Atomic switch + restart
ln -sfn $RELEASE_DIR /home/ai/$PROJECT_NAME/current
sudo systemctl restart $PROJECT_NAME

# Health (čekaj duže — model preload)
sleep 10
curl -fsS https://$DOMAIN/healthz && echo "✅ DEPLOY OK" || {
    echo "❌ Health failed"
    sudo journalctl -u $PROJECT_NAME -n 50 --no-pager
}

# Cleanup zadnjih 5
cd /home/ai/$PROJECT_NAME/releases
ls -t | tail -n +6 | xargs -r rm -rf
```

---

## 12. Troubleshooting — naše specifičnosti

| Simptom | Diagnoza |
|---|---|
| Prvi `/api/chat` poslije restarta vraća error / "Pretraga prazan rezultat" | sentence-transformers model još uvijek loaduje (~30-50s prvi put). Sledeći upit ide normalno. Provjera: `journalctl -u $PROJECT_NAME --since "1 min ago" \| grep -i "loading\|cache"`. |
| `data/products.index.npz` nedostaje | Fajl je u `.gitignore`. Regeneriši: `cd /home/ai/$PROJECT_NAME/current && .venv/bin/python scripts/embed_products.py`. Pa pomjeri u shared/var. |
| Dashboard `/admin/` daje 404 | Provjeri symlink: `readlink -f /home/ai/$PROJECT_NAME/current/dashboard/dist/index.html`. Ako fali, `cd dashboard && pnpm build`. |
| Dashboard `/api/dashboard/*` daje 401 | Nedostaje `DASHBOARD_API_KEY` u .env ili pogrešan token u UI Settings. |
| Compare endpoint timeout | Sonnet poziv može trajati 15-20s. nginx `proxy_read_timeout 120s` bi trebao biti dovoljno; provjeri da je u config-u. |
| Voice TTS 503 | Azure ključ nedostaje ili ne radi. Fallback edge-tts (besplatan) trebao bi raditi bez ključa. Test: `curl -X POST .../api/tts -d '{"text":"test"}'`. |
| TTS čita "1.936 KM" kao "jedna marka" | Sesija 8 hotfix u `app/main.py:_normalize_for_tts`. Ako je server na starom kodu, treba re-deploy. Test: `python -m pytest tests/test_tts_normalization.py`. |
| `<voice>` tagovi se vide u chat output | Sesija 8 hotfix u `app/agent.py:_strip_voice_tags`. Hard refresh widget-a u browser-u (Ctrl+Shift+R) za widget cache. |
| `rsync` koji image_url? | Ne, slika je 7.2% missing iz webshop CDN-a (data quality). Audit ih označava, rag.py vraća None. Vidi `data/missing_images.json`. |
| Cron za auto-refresh kataloga | Nije postavljeno. Predlog: dodati `cron` koji jednom sedmično `git pull && bash scripts/deploy.sh update` — u Sesiji 11. |

---

## 13. Webshop integracija (poslije zelenog deploy-a)

Doda se **jedan `<script>` tag** na `webshop.bitlab.rs` HTML (pred `</body>`):

```html
<script src="https://aiasistent.bitlab.rs/public/widget.js"></script>
```

**Pre toga:**
- CSP webshop-a mora dozvoliti `aiasistent.bitlab.rs` u `script-src` i `connect-src` (za fetch ka `/api/chat`).
- Provjeri postojeće `Content-Security-Policy` header webshop-a.

**Test integracije:**
- Otvori webshop u browser-u
- Provjeri u DevTools Network tab → `widget.js` learn 200
- Klikni floating chat dugme → otvori se modal → pošalji poruku → odgovor stiže

---

## 14. Open questions koje server-side Claude prije izvršenja MORA potvrditi sa Ivanom

Pitaj ovih 5 pitanja prije Sekcije 6:

1. **Je li `production-prep` PR merge-ovan na `main` ili krećemo sa `production-prep` granom?** (utiče na `BRANCH` env var u Sekciji 1)
2. **Postoji li već `aiasistent-staging` u nekom obliku, ili kreiramo greenfield?** (utiče na backup u Sekciji 10)
3. **Gdje su trenutno `.env` ključevi za prod legacy?** Treba ih reuse-ovati ili rotirati?
4. **Da li webshop CSP dozvoljava cross-origin script + fetch sa `aiasistent.bitlab.rs`?** Ako ne, ili Ivan dodaje, ili koristimo drugi pristup (npr. proxy /widget.js kroz webshop server).
5. **Backup rotacija — koliko dana da držimo `_backups/`?** Default 30 dana (sa `find _backups -mtime +30 -delete` u cronu).

---

## 15. Za PR review (kad merge-ujemo `production-prep` → `main`)

PR opis treba pomenuti:
- ✅ Sva Sesija 8 funkcionalnost (kategorije, dashboard, voice UX, hotfixovi)
- ✅ Server deploy artefakti (ovaj fajl, `DEPLOY_GUIDE.md`, `scripts/deploy.sh`, `deploy/*`)
- ✅ Open rezolucije (Sesija 9 model eval, Sesija 10 growth)
- ⚠️ **Server-side install ostaje TODO** — radimo poslije merge-a u zasebnoj sesiji sa server-side Claude instancom

---

## Verzija dokumenta

`SERVER-DEPLOY-PLAN.md` v1.0 · 2026-05-04
Master ref: `DEPLOY_GUIDE.md` v1.0
Sinkronizovan sa: branch `production-prep` HEAD ~`49a4e5a`
