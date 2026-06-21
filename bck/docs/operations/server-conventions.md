# Deploy Guide — ai.bitlab.rs VPS

Ovaj dokument je instrukcija za **deploy novog projekta** na server `ai.bitlab.rs`.
Namijenjen je za izvršavanje od strane čovjeka **ili** od strane Claude Code agenta (one-shot deploy).

---

## 0. Server context (NE MIJENJAJ)

```yaml
host:           ai.bitlab.rs
user:           ai            # ima sudo
os:             Debian/Ubuntu
project_root:   /home/ai/
nginx_config:   /etc/nginx/hosts/    # NE /etc/nginx/sites-available/
already_installed:
  - nginx
  - certbot (python3-certbot-nginx)
  - docker + docker compose
  - python3 + python3-venv
  - git
```

---

## 1. Domeni & port mapa

### 1.1 Domeni (iz DNS-a)

| Domena                              | Tip        | Status         |
|-------------------------------------|------------|----------------|
| aiasistent.bitlab.rs                | prod       | postoji (legacy bez symlinka) |
| staging.aiasistent.bitlab.rs        | staging    | postoji (symlink pattern)     |
| compliance.bitlab.rs                | prod       | TODO           |
| staging.compliance.bitlab.rs        | staging    | TODO           |

### 1.2 Port mapa — REZERVISANO

> ⚠️ **Pravilo:** dva servisa NIKAD ne smiju koristiti isti port. Prije deploya provjeri:
> `sudo ss -tlnp | grep :PORT`

| Port range | Namjena                                     |
|-----------|---------------------------------------------|
| 8000      | aiasistent-prod (`bitlab-ai.service`)       |
| 8001      | aiasistent-staging                          |
| 8002      | compliance-prod (gateway)                   |
| 8003      | compliance-staging (gateway)                |
| 8010-8019 | compliance-prod interni mikroservisi        |
| 8020-8029 | compliance-staging interni mikroservisi     |
| 8030+     | rezervisano za buduće projekte              |

> 🔒 **Sigurnost:** svi app portovi slušaju samo na `127.0.0.1`, NIKAD na `0.0.0.0`.
> Jedini servis izložen javno je nginx (80/443).

---

## 2. Struktura foldera (symlink pattern, zero-downtime)

Svaki projekat ima istu strukturu:

```
/home/ai/<PROJECT_NAME>/
├── releases/
│   ├── 20260501_1830/        # stari release (može za rollback)
│   ├── 20260502_0915/        # noviji
│   └── 20260502_1430/        # najnoviji
├── shared/                   # ono što preživi između releaseva
│   ├── .env                  # tajne, DB pristupi (NE u git-u)
│   ├── logs/
│   ├── uploads/              # ako app prima file uploade
│   └── postgres-data/        # samo Pattern B
└── current -> releases/20260502_1430/    # ATOMIC SYMLINK
```

**Ključna ideja:** nginx i systemd uvijek pokazuju na `current/`. Deploy = atomično prebaci symlink.

---

## 3. Dva pattern-a deploya

### Kako odabrati?

| Slučaj                                       | Pattern |
|---------------------------------------------|---------|
| Jedan Python (FastAPI) servis               | **A**   |
| Više servisa, baza, Redis, message queue... | **B**   |

- **Pattern A** — venv + systemd + symlink → koristi za `aiasistent-*`
- **Pattern B** — Docker Compose + symlink → koristi za `compliance-*`

---

# 🅰️ Pattern A — Single FastAPI app

## A.1 Varijable za popunjavanje

Prije izvršavanja **POPUNI** ove vrijednosti (Claude Code: ovo su ulazni parametri):

```bash
# === POPUNI ===
export PROJECT_NAME="aiasistent-staging"             # folder pod /home/ai/
export DOMAIN="staging.aiasistent.bitlab.rs"         # FQDN
export PORT="8001"                                    # iz port mape (sekcija 1.2)
export REPO_URL="git@github.com:bitlab/repo.git"     # git ssh ili https
export BRANCH="main"                                  # git branch
export ENTRY_POINT="app.main:app"                    # Python modul:objekt za uvicorn
export ADMIN_EMAIL="admin@bitlab.rs"                 # za Let's Encrypt
# === KRAJ ===
```

> 💡 `ENTRY_POINT` se određuje na osnovu strukture repo-a:
> - `repo/app/main.py` koji ima `app = FastAPI()` → `app.main:app`
> - `repo/cm_scraper/app.py` koji ima `app = FastAPI()` → `cm_scraper.app:app`

## A.2 Provjere PRIJE deploya

```bash
# 1. Port slobodan?
sudo ss -tlnp | grep ":$PORT " && echo "❌ PORT zauzet" || echo "✅ PORT slobodan"

# 2. Domena resolva na ovaj server?
SERVER_IP=$(curl -s ifconfig.me)
DNS_IP=$(dig +short $DOMAIN | tail -1)
[ "$SERVER_IP" = "$DNS_IP" ] && echo "✅ DNS OK" || echo "❌ DNS pokazuje na $DNS_IP, server je $SERVER_IP"

# 3. Project folder već postoji?
[ -d /home/ai/$PROJECT_NAME ] && echo "⚠️  Folder već postoji" || echo "✅ Folder slobodan"
```

Ako bilo koja provjera padne — **STANI** i riješi prije nastavka.

## A.3 Inicijalna struktura (samo prvi put)

```bash
mkdir -p /home/ai/$PROJECT_NAME/releases
mkdir -p /home/ai/$PROJECT_NAME/shared/logs
mkdir -p /home/ai/$PROJECT_NAME/shared/uploads

# Kreiraj prazan .env (popuniš ga u sljedećem koraku)
touch /home/ai/$PROJECT_NAME/shared/.env
chmod 600 /home/ai/$PROJECT_NAME/shared/.env

ls -la /home/ai/$PROJECT_NAME/
```

## A.4 Popuni shared/.env

```bash
nano /home/ai/$PROJECT_NAME/shared/.env
```

Primjer sadržaja (prilagodi za svoju app):

```env
ENV=staging
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=...
OPENAI_API_KEY=...
```

## A.5 Inicijalni release

```bash
RELEASE=$(date +%Y%m%d_%H%M)
RELEASE_DIR=/home/ai/$PROJECT_NAME/releases/$RELEASE
echo "📦 Release: $RELEASE"

# Clone repo
git clone -b $BRANCH $REPO_URL $RELEASE_DIR
cd $RELEASE_DIR

# Symlink .env iz shared/ (ne kopiranje — uvijek čita najnoviji)
ln -sfn /home/ai/$PROJECT_NAME/shared/.env $RELEASE_DIR/.env

# Symlink uploads ako app koristi
# ln -sfn /home/ai/$PROJECT_NAME/shared/uploads $RELEASE_DIR/uploads

# Build venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
# ako repo koristi pyproject.toml: pip install -e .

# (opcionalno) DB migracije
# alembic upgrade head

# (opcionalno) Smoke test
# python -c "from $ENTRY_POINT" || { echo "❌ Import failed"; exit 1; }

# Atomic switch — od sada current pokazuje na ovaj release
ln -sfn $RELEASE_DIR /home/ai/$PROJECT_NAME/current

# Provjeri
ls -la /home/ai/$PROJECT_NAME/current
readlink -f /home/ai/$PROJECT_NAME/current
```

## A.6 Systemd servis

```bash
sudo tee /etc/systemd/system/$PROJECT_NAME.service > /dev/null <<EOF
[Unit]
Description=$PROJECT_NAME (FastAPI on $DOMAIN, port $PORT)
After=network.target

[Service]
Type=simple
User=ai
Group=ai
WorkingDirectory=/home/ai/$PROJECT_NAME/current
EnvironmentFile=/home/ai/$PROJECT_NAME/current/.env
ExecStart=/home/ai/$PROJECT_NAME/current/.venv/bin/uvicorn $ENTRY_POINT --host 127.0.0.1 --port $PORT --workers 2
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$PROJECT_NAME

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $PROJECT_NAME
sudo systemctl start $PROJECT_NAME

# Sačekaj da app starta
sleep 3

# Provjera
sudo systemctl status $PROJECT_NAME --no-pager
sudo journalctl -u $PROJECT_NAME -n 30 --no-pager

# Test direktno na port
curl -sf http://127.0.0.1:$PORT/health 2>/dev/null \
  || curl -sf http://127.0.0.1:$PORT/ \
  || echo "⚠️  App ne odgovara na $PORT"
```

## A.7 Nginx config (HTTP, prije SSL)

```bash
sudo tee /etc/nginx/hosts/$PROJECT_NAME.conf > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    access_log /home/ai/$PROJECT_NAME/shared/logs/nginx-access.log;
    error_log  /home/ai/$PROJECT_NAME/shared/logs/nginx-error.log;
}
EOF

sudo nginx -t || { echo "❌ Nginx config invalid"; exit 1; }
sudo systemctl reload nginx

# Test HTTP
curl -I http://$DOMAIN
```

## A.8 SSL certifikat (Let's Encrypt)

```bash
sudo certbot --nginx \
  -d $DOMAIN \
  --non-interactive \
  --agree-tos \
  --email $ADMIN_EMAIL \
  --redirect

# Test HTTPS
curl -I https://$DOMAIN

# Provjeri auto-renewal
sudo certbot renew --dry-run
```

## A.9 Re-deploy (svaki sljedeći put)

```bash
# Pretpostavlja da su PROJECT_NAME, REPO_URL, BRANCH već exportovani
RELEASE=$(date +%Y%m%d_%H%M)
RELEASE_DIR=/home/ai/$PROJECT_NAME/releases/$RELEASE

git clone -b $BRANCH $REPO_URL $RELEASE_DIR
cd $RELEASE_DIR

# Symlink .env
ln -sfn /home/ai/$PROJECT_NAME/shared/.env $RELEASE_DIR/.env

# Build
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt

# (opciono) testovi prije switcha
# pytest tests/ -q || { echo "❌ Testovi pali"; exit 1; }

# Atomic switch
ln -sfn $RELEASE_DIR /home/ai/$PROJECT_NAME/current

# Restart servisa
sudo systemctl restart $PROJECT_NAME

# Health check
sleep 5
curl -sf https://$DOMAIN/health && echo "✅ DEPLOY OK" || {
  echo "❌ Health check failed — razmotri rollback"
  sudo journalctl -u $PROJECT_NAME -n 50 --no-pager
}

# Cleanup — čuvaj zadnjih 5 releasa
cd /home/ai/$PROJECT_NAME/releases
ls -t | tail -n +6 | xargs -r rm -rf
```

---

# 🅱️ Pattern B — Microservices (Docker Compose)

## B.1 Varijable

```bash
# === POPUNI ===
export PROJECT_NAME="compliance-staging"
export DOMAIN="staging.compliance.bitlab.rs"
export GATEWAY_PORT="8003"                            # iz port mape
export INTERNAL_PORT_BASE="8020"                      # 8020-8029 za staging, 8010-8019 za prod
export REPO_URL="git@github.com:bitlab/compliance.git"
export BRANCH="main"
export ADMIN_EMAIL="admin@bitlab.rs"
# === KRAJ ===
```

## B.2 Provjere

```bash
# Port slobodan?
sudo ss -tlnp | grep ":$GATEWAY_PORT " && echo "❌ ZAUZETO" || echo "✅ OK"

# Docker radi?
docker ps > /dev/null && echo "✅ Docker OK" || echo "❌ Docker problem"

# Domena resolva?
dig +short $DOMAIN
```

## B.3 Inicijalna struktura

```bash
mkdir -p /home/ai/$PROJECT_NAME/releases
mkdir -p /home/ai/$PROJECT_NAME/shared/logs
mkdir -p /home/ai/$PROJECT_NAME/shared/postgres-data
mkdir -p /home/ai/$PROJECT_NAME/shared/redis-data       # ako koristi Redis
mkdir -p /home/ai/$PROJECT_NAME/shared/uploads          # ako prima uploads

touch /home/ai/$PROJECT_NAME/shared/.env
chmod 600 /home/ai/$PROJECT_NAME/shared/.env

ls -la /home/ai/$PROJECT_NAME/
```

## B.4 Popuni shared/.env

```bash
nano /home/ai/$PROJECT_NAME/shared/.env
```

Primjer:

```env
ENV=staging

# Postgres
POSTGRES_USER=compliance
POSTGRES_PASSWORD=<jaka-lozinka>
POSTGRES_DB=compliance

# App tajne
SECRET_KEY=<...>
JWT_SECRET=<...>

# Vanjske API
OPENAI_API_KEY=<...>
```

## B.5 Provjeri / prilagodi `docker-compose.yml`

> ⚠️ Ovo je **NAJVAŽNIJI** korak Pattern B. Klonaj repo, otvori `docker-compose.yml`,
> i osiguraj sljedeće:

**Pravila:**

1. **Samo gateway izlaže port na host** — i to **isključivo** na `127.0.0.1`:
   ```yaml
   gateway:
     ports:
       - "127.0.0.1:${GATEWAY_PORT}:8000"   # ✅ samo lokalno
   ```
   **NIKAD** `"8003:8000"` ili `"0.0.0.0:8003:8000"` — to izlaže port javno.

2. **Ostali servisi NEMAJU `ports:`** — komuniciraju kroz Docker network:
   ```yaml
   service-auth:
     # bez ports: !!!
     networks:
       - internal
   ```

3. **Volumes za stanje idu u shared/**:
   ```yaml
   postgres:
     volumes:
       - /home/ai/compliance-staging/shared/postgres-data:/var/lib/postgresql/data
   ```

4. **Svi servisi koriste `.env`**:
   ```yaml
   service-x:
     env_file: .env
   ```

Primjer minimalnog ispravnog `docker-compose.yml`:

```yaml
services:
  gateway:
    build: ./gateway
    ports:
      - "127.0.0.1:${GATEWAY_PORT}:8000"
    depends_on:
      - service-a
      - service-b
      - postgres
      - redis
    networks:
      - internal
    env_file: .env
    restart: always

  service-a:
    build: ./service-a
    networks:
      - internal
    env_file: .env
    depends_on:
      - postgres
    restart: always

  service-b:
    build: ./service-b
    networks:
      - internal
    env_file: .env
    restart: always

  service-c:
    build: ./service-c
    networks:
      - internal
    env_file: .env
    restart: always

  service-d:
    build: ./service-d
    networks:
      - internal
    env_file: .env
    restart: always

  postgres:
    image: postgres:16
    volumes:
      - /home/ai/${COMPOSE_PROJECT_NAME}/shared/postgres-data:/var/lib/postgresql/data
    networks:
      - internal
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    restart: always

  redis:
    image: redis:7-alpine
    volumes:
      - /home/ai/${COMPOSE_PROJECT_NAME}/shared/redis-data:/data
    networks:
      - internal
    restart: always

networks:
  internal:
    driver: bridge
```

## B.6 Inicijalni release

```bash
RELEASE=$(date +%Y%m%d_%H%M)
RELEASE_DIR=/home/ai/$PROJECT_NAME/releases/$RELEASE

git clone -b $BRANCH $REPO_URL $RELEASE_DIR
cd $RELEASE_DIR

# Symlink .env iz shared/
ln -sfn /home/ai/$PROJECT_NAME/shared/.env $RELEASE_DIR/.env

# Build sve image-ove
docker compose --env-file .env -p $PROJECT_NAME build

# Start (detached)
docker compose --env-file .env -p $PROJECT_NAME up -d

# Sačekaj inicijalizaciju (DB, migracije...)
sleep 15

# Provjera
docker compose -p $PROJECT_NAME ps
docker compose -p $PROJECT_NAME logs --tail=50

# Atomic switch — tek nakon što su svi up
ln -sfn $RELEASE_DIR /home/ai/$PROJECT_NAME/current

# Test gateway-a
curl -sf http://127.0.0.1:$GATEWAY_PORT/health \
  && echo "✅ Gateway OK" \
  || echo "❌ Gateway ne odgovara"
```

## B.7 Nginx config + SSL

**Ista procedura kao A.7 i A.8** — koristi `$GATEWAY_PORT` umjesto `$PORT`:

```bash
sudo tee /etc/nginx/hosts/$PROJECT_NAME.conf > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:$GATEWAY_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
    }

    access_log /home/ai/$PROJECT_NAME/shared/logs/nginx-access.log;
    error_log  /home/ai/$PROJECT_NAME/shared/logs/nginx-error.log;
}
EOF

sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d $DOMAIN \
  --non-interactive --agree-tos --email $ADMIN_EMAIL --redirect

curl -I https://$DOMAIN
```

## B.8 Re-deploy (Pattern B)

> 💡 Pattern B nije true zero-downtime osim sa Blue/Green setup-om (dva paralelna
> docker compose project name-a sa različitim portovima). Za staging je
> ~30s downtime prihvatljivo. Za pravi zero-downtime na compliance-prod —
> pitaj da dopunim guide sa Blue/Green sekcijom.

```bash
RELEASE=$(date +%Y%m%d_%H%M)
RELEASE_DIR=/home/ai/$PROJECT_NAME/releases/$RELEASE

git clone -b $BRANCH $REPO_URL $RELEASE_DIR
cd $RELEASE_DIR
ln -sfn /home/ai/$PROJECT_NAME/shared/.env $RELEASE_DIR/.env

# Build novih image-ova (stari kontejneri još rade)
docker compose --env-file .env -p $PROJECT_NAME build

# Down + up (downtime starts here)
cd /home/ai/$PROJECT_NAME/current
docker compose --env-file .env -p $PROJECT_NAME down

cd $RELEASE_DIR
docker compose --env-file .env -p $PROJECT_NAME up -d
sleep 15

# Switch symlink
ln -sfn $RELEASE_DIR /home/ai/$PROJECT_NAME/current

# Health
docker compose -p $PROJECT_NAME ps
curl -sf https://$DOMAIN/health && echo "✅ DEPLOY OK"

# Cleanup
cd /home/ai/$PROJECT_NAME/releases
ls -t | tail -n +6 | xargs -r rm -rf

# Cleanup unused docker images
docker image prune -f
```

---

# 📋 Standardne procedure

## Rollback (Pattern A)

```bash
PROJECT_NAME="aiasistent-staging"

# Vidi releaseve
ls -lt /home/ai/$PROJECT_NAME/releases/

# Switch (zamijeni TIMESTAMP)
PREV="20260502_0915"
ln -sfn /home/ai/$PROJECT_NAME/releases/$PREV /home/ai/$PROJECT_NAME/current
sudo systemctl restart $PROJECT_NAME
sudo systemctl status $PROJECT_NAME --no-pager
```

## Rollback (Pattern B)

```bash
PROJECT_NAME="compliance-staging"
PREV="20260502_0915"

cd /home/ai/$PROJECT_NAME/current
docker compose -p $PROJECT_NAME down

cd /home/ai/$PROJECT_NAME/releases/$PREV
docker compose --env-file .env -p $PROJECT_NAME up -d

ln -sfn /home/ai/$PROJECT_NAME/releases/$PREV /home/ai/$PROJECT_NAME/current
```

## Provjera koji release je aktivan

```bash
readlink -f /home/ai/$PROJECT_NAME/current
```

## Logovi

```bash
# Pattern A (systemd)
sudo journalctl -u $PROJECT_NAME -f
sudo journalctl -u $PROJECT_NAME -n 100 --no-pager

# Pattern B (Docker)
docker compose -p $PROJECT_NAME logs -f --tail=100
docker compose -p $PROJECT_NAME logs SERVICE_NAME -f

# Nginx (oba pattern-a)
tail -f /home/ai/$PROJECT_NAME/shared/logs/nginx-access.log
tail -f /home/ai/$PROJECT_NAME/shared/logs/nginx-error.log
```

## Status servisa

```bash
# Sve systemd servise
sudo systemctl list-units --type=service | grep -E "aiasistent|compliance|bitlab"

# Sve Docker projekte
docker compose ls

# Svi nginx host fajlovi
ls -la /etc/nginx/hosts/

# Svi otvoreni portovi
sudo ss -tlnp
```

---

# ✅ Final checklist za novi deploy

Pre nego što kreneš:

- [ ] Odabran pattern (A za single FastAPI, B za microservices)
- [ ] Sve varijable popunjene
- [ ] PORT slobodan (`sudo ss -tlnp | grep PORT`)
- [ ] DNS A record za DOMAIN postavljen na server IP
- [ ] Imaš git pristup repo-u (SSH ključ ako je `git@`)

Tokom deploya:

- [ ] Folder struktura kreirana (`releases/`, `shared/`)
- [ ] `shared/.env` popunjen sa svim potrebnim env varijablama
- [ ] Inicijalni release clone-an i build-an
- [ ] Symlink `current` postavljen
- [ ] Systemd servis (A) ili Docker Compose (B) up
- [ ] Health check na `127.0.0.1:PORT` prolazi
- [ ] Nginx config kreiran u `/etc/nginx/hosts/`
- [ ] `nginx -t` prolazi
- [ ] `nginx reload` urađen
- [ ] HTTP test: `curl -I http://DOMAIN` → 200/30x
- [ ] Certbot SSL urađen
- [ ] HTTPS test: `curl -I https://DOMAIN` → 200/30x
- [ ] Auto-renewal test: `sudo certbot renew --dry-run`

Nakon deploya:

- [ ] Cleanup starih releasea (čuvaj zadnjih 5)
- [ ] Dokumentuj port i domenu u port mapi (sekcija 1.2)

---

# 🆘 Troubleshooting

| Simptom | Diagnoza |
|---------|----------|
| `nginx -t` failuje | Provjeri syntax u `/etc/nginx/hosts/*.conf`, posebno `;` na kraju linija |
| `curl http://DOMAIN` → 502 Bad Gateway | App nije up. `sudo systemctl status PROJECT_NAME` ili `docker compose ps` |
| `curl http://DOMAIN` → 404 | Nginx ne matchuje server_name. Provjeri da li je config u `/etc/nginx/hosts/` i da li je `server_name` tačan |
| `certbot` failuje | Provjeri da li domena resolva na ovaj server: `dig +short DOMAIN` |
| Browser kaže "ERR_CERT_COMMON_NAME_INVALID" | Certifikat je za drugu domenu — generiši poseban certbot za ovu domenu |
| `sudo systemctl start` failuje | `sudo journalctl -u PROJECT_NAME -n 50 --no-pager` — vidi tačan error |
| Docker servisi se ne povezuju | Provjeri da li su svi u istom `networks: [internal]` |
| Promjene u kodu se ne vide | Servis nije restart-ovan ili symlink ne pokazuje na novi release. `readlink -f current` |

---

**Verzija dokumenta:** 1.0
**Posljednja izmjena:** 2026-05-04
