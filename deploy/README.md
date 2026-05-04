# BitLab AI Asistent — Server-side deploy checklist

> Ovaj dokument je za **Claude Code instancu instaliranu na samom serveru**
> (ne za lokalnu razvojnu mašinu). Lokalna sesija priprema artefakte
> (`scripts/deploy.sh`, `deploy/*`) — server-side sesija ih izvršava sa
> direktnim shell pristupom.

---

## 0. ⚠️ PRVO: Ivanov server, Ivanova pravila

**Server već hostuje 4 druge aplikacije, svaka na svom domenu.** Konvencije
(layout direktorijuma, naming, user accounts, port alokacija, nginx struktura,
SSL setup, logging) **već postoje** — naš deploy mora da im se prilagodi, NE
obrnuto.

**Prije nego što izvršiš ijedan korak iz Sekcija 1+ ovog dokumenta:**

1. Pitaj Ivana da objasni server pravila:
   - Gdje žive servisi (`/opt/`, `/srv/`, `/var/www/`, drugo)?
   - Koji service user (`www-data`, jedan zajednički, per-app, drugo)?
   - Kako se rezervišu portovi (npr. opseg 8000-8999, ili manuelni registar)?
   - nginx layout: `sites-available/<app>` ili nešto custom (npr. `conf.d/<app>.conf`)?
   - SSL: certbot per-domen ili wildcard?
   - Logging konvencija: `/var/log/<app>/`, journald only, custom?
   - venv per-app ili shared interpreter?
   - Backup / rollback strategija postojećih app-ova
2. **Ažuriraj sledeće fajlove da poštuju te konvencije** prije izvršenja:
   - `scripts/deploy.sh` — top-level varijable `PROJECT_DIR`, `SERVICE_USER`, `DASHBOARD_DIST_TARGET`
   - `deploy/bitlab-ai.service` — `User=`, `Group=`, `WorkingDirectory=`, `EnvironmentFile=`, `ExecStart=` putanja
   - `deploy/nginx-site.conf` — putanja do `dist/`, log paths, lokacija site fajla
3. Tek onda izvršavaj korake iz Sekcije 1.

**Default-i u trenutnim artefaktima** (i šta da provjeriš):

| Artefakt | Default | Vjerovatno treba promijeniti? |
|---|---|---|
| `PROJECT_DIR` | `/opt/bitlab-ai` | Da li ostali servisi žive u `/opt/` ili negdje drugo? |
| `SERVICE_USER` | `bitlab` (poseban) | Možda je konvencija jedan zajednički user (`www-data`)? |
| Port | `127.0.0.1:8000` | Već zauzet od neke od 4 app? Provjeri `ss -ltnp` |
| `DASHBOARD_DIST_TARGET` | `/var/www/bitlab-admin/` | Da li drugi koriste isti pattern ili `/srv/www/`? |
| `bitlab-ai.service` u `/etc/systemd/system/` | da | OK po default-u |
| nginx site | `/etc/nginx/sites-available/bitlab-ai` + symlink | Provjeri konvenciju (`conf.d/` ili `sites-`) |
| nginx logs | `/var/log/nginx/bitlab-ai.access.log` | Možda postoji centralizovana lokacija |

**Princip:** ne pravimo novi standard kad već postoji. Sve što ne kvari našu
funkcionalnost prilagođavamo. Ako neka konvencija stvara problem za naš stack
(npr. neko forsira sync WSGI a mi imamo async FastAPI sa lifespan task-ovima),
tek onda raspravljamo.

---

## 1. Preduslovi (uradi ručno prije nego što me kontaktiraš)

1. VPS sa **Ubuntu 22.04+** ili Debian 12+
2. **Python 3.11+** instaliran (`python3 --version`)
3. **Node 22 LTS i pnpm** instalirani (za dashboard build):
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
   sudo apt-get install -y nodejs
   sudo npm i -g pnpm
   node -v   # mora v22.x
   ```
   Ako već imaš stari Node (v20), prvo očisti repo:
   ```bash
   sudo rm -f /etc/apt/sources.list.d/nodesource.list /etc/apt/keyrings/nodesource.gpg
   ```
   pa onda gornji setup_22 komandu.
4. **nginx i certbot**:
   ```bash
   sudo apt install -y nginx certbot python3-certbot-nginx rsync
   ```
5. Domen pokazuje na VPS IP (A record)
6. Repo klon na server:
   ```bash
   sudo git clone https://github.com/<owner>/bitlab-ai-asistent /opt/bitlab-ai
   cd /opt/bitlab-ai && sudo git checkout production-prep
   ```
7. **`.env` popunjen** sa svim ključevima:
   ```bash
   sudo cp .env.example .env
   sudo nano .env
   ```
   Obavezno popuniti:
   - `ANTHROPIC_API_KEY=sk-ant-...`
   - `DASHBOARD_API_KEY=` (generiši: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)
   - Opciono: `AZURE_SPEECH_KEY`, `GROQ_API_KEY` (TTS/STT fallback chain)

---

## Prvi install

```bash
cd /opt/bitlab-ai
sudo bash scripts/deploy.sh install
```

Skripta će:
1. Kreirati `bitlab` service user-a
2. Napraviti `.venv/` i instalirati Python deps (CPU-only torch ~180MB, prvi put 3+ min)
3. Generisati `data/categories.json` (ako nedostaje)
4. Inicijalizovati `var/bitlab.db` schema
5. Build-ovati `dashboard/dist/` (Vite + tsc, ~30s)
6. Publish-ovati u `/var/www/bitlab-admin/`
7. Instalirati `bitlab-ai.service` (systemd, enable + start)
8. Instalirati nginx site config (treba ručno zameniti placeholder)
9. Restart + smoke test (curl /healthz)

**Poslije install-a obavezno:**

```bash
# 1. Zameni placeholder za pravi domen
sudo sed -i "s/AI_DOMAIN_PLACEHOLDER/ai.bitlab.rs/g" /etc/nginx/sites-available/bitlab-ai

# 2. SSL cert
sudo certbot --nginx -d ai.bitlab.rs

# 3. Reload nginx
sudo nginx -t && sudo systemctl reload nginx

# 4. Smoke test eksterno
curl -fsS https://ai.bitlab.rs/healthz
```

**Kritičan korak:** product index. Ako nije bio rsync-ovan iz lokalne mašine,
mora se izgenerisati na serveru:

```bash
# Treba ~5GB diska + 5min CPU
sudo -u bitlab /opt/bitlab-ai/.venv/bin/python /opt/bitlab-ai/scripts/embed_products.py
sudo systemctl restart bitlab-ai
```

---

## Update flow (svaki sledeći deploy)

```bash
cd /opt/bitlab-ai
sudo bash scripts/deploy.sh update
```

- `git pull` na trenutnu granu
- Reinstall Python deps ako se `pyproject.toml` promijenio
- Regeneriše `data/categories.json` ako nedostaje
- Init DB (idempotentno; nove tabele se dodaju)
- Rebuild dashboard
- Restart service
- Smoke test

---

## Samo rebuild dashboard-a (npr. UI fix)

```bash
sudo bash scripts/deploy.sh rebuild
```

---

## Rollback

```bash
cd /opt/bitlab-ai
sudo -u bitlab git log --oneline -10                  # nađi prethodni commit
sudo -u bitlab git checkout <hash>
sudo bash scripts/deploy.sh update
```

---

## Provjera zdravlja

```bash
# Service status
systemctl status bitlab-ai

# Nedavni logovi
journalctl -u bitlab-ai -n 100 --no-pager

# Health check
curl -fsS http://127.0.0.1:8000/healthz | jq

# Dashboard auth test
curl -fsS -H "Authorization: Bearer $(grep ^DASHBOARD_API_KEY /opt/bitlab-ai/.env | cut -d= -f2)" \
  http://127.0.0.1:8000/api/dashboard/stats | jq

# nginx error log
tail -50 /var/log/nginx/bitlab-ai.error.log
```

---

## Tipični problemi

### `sentence-transformers` model na startup-u traje predugo
Prvi `/api/chat` čeka da se `paraphrase-multilingual-MiniLM-L12-v2` skine i loaduje.
Na VPS-u sa SSD-om: ~30-50s. Ova greška je benigna (vidi se u Live tabu kao
"error" iz prvog poziva — sledeći ide normalno). Da se preempt-uje:

```bash
sudo -u bitlab /opt/bitlab-ai/.venv/bin/python -c "
from app.rag import get_index
get_index().preload_model()
print('model warm')
"
```

### `data/products.index.npz` nedostaje
Na lokalnoj mašini ide kroz `.gitignore` (file je 16MB). Na serveru:

```bash
# Opcija A: rsync iz lokalne mašine
rsync -av data/products.* user@vps:/opt/bitlab-ai/data/

# Opcija B: regeneriši na serveru (treba ~5GB diska + 5min CPU)
sudo -u bitlab /opt/bitlab-ai/.venv/bin/python /opt/bitlab-ai/scripts/embed_products.py
```

### Dashboard 404 ili stari sadržaj
nginx kešira asset-e 1 godinu (immutable hash u imenu). Ako vidiš stari UI:
- Hard refresh u browser-u (Ctrl+Shift+R)
- Ili `sudo bash scripts/deploy.sh rebuild` da regeneriše hash-eve

### `bitlab-ai.service` ne pokreće
```bash
journalctl -u bitlab-ai -n 200 --no-pager
```
Najčešći uzroci:
- `.env` nije čitljiv user-u `bitlab` (`sudo chown -R bitlab:bitlab /opt/bitlab-ai`)
- Port 8000 zauzet (`sudo ss -ltnp | grep 8000`)
- `var/` direktorijum nije zapisiv (`sudo mkdir -p var && sudo chown -R bitlab:bitlab var`)

---

## Tipovi servisa koje će ovaj setup hostovati

Trenutno:
- `bitlab-ai.service` — FastAPI (chat + voice + email + dashboard API)
- nginx (reverse proxy + static dashboard)

Planirano (sljedeće mikro-servise dodajemo istom skriptom):
- `bitlab-n8n.service` — lokalni n8n umjesto cloud-a (P2)
- `bitlab-monitoring.service` — health endpoint scraper (P3)
- `bitlab-embed-cron.timer` — automatski rebuild product indexa noću (P3)

Svaki novi servis dobija svoj `deploy/<name>.service` i koraka u
`scripts/deploy.sh` — pa je deploy uvijek jedan `sudo bash scripts/deploy.sh update`.
