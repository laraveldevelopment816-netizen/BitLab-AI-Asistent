# BitLab AI Asistent — VPS Deployment Guide

Ovaj dokument pokriva kompletno postavljanje na VPS server:
- Python servis (systemd, auto-start)
- Nginx reverse proxy + SSL
- n8n lokalno na serveru (bez ngroka)
- Konekcija na postojeću webshop MySQL bazu
- Automatsko osvježavanje kataloga

---

## Preduslovi

| Resurs | Minimalno | Preporučeno |
|--------|-----------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disk | 5 GB | 10 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Python | 3.11+ | 3.11+ |

> **Zašto 1 GB RAM?** Embedding model (`MiniLM-L12-v2`) zauzima ~350 MB pri startu. Na 1 GB sistemu ostavlja dovoljno prostora za FastAPI + n8n ako se n8n hostuje posebno.

Provjeri Python verziju na serveru:

```bash
python3 --version
```

Ako je verzija < 3.11 (npr. Ubuntu 20.04 ima 3.8):

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-distutils -y
```

---

## 1. Postavljanje projekta na VPS

### Konekcija i kloniranje

```bash
ssh user@YOUR-VPS-IP

# Kloniranje u /opt (sistemska lokacija za servise)
cd /opt
sudo git clone https://github.com/tvoj-username/bitlab-ai-asistent.git
sudo chown -R $USER:$USER /opt/bitlab-ai-asistent
cd /opt/bitlab-ai-asistent
```

### Virtuelno okruženje i zavisnosti

```bash
python3.11 -m venv .venv
source .venv/bin/activate

# CPU-only PyTorch (~180MB) — OBAVEZNO PRVO
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Ostale zavisnosti
pip install -e .
```

### Konfiguracija (.env)

```bash
cp .env.example .env
nano .env
```

Popuni `.env` (format `KEY=VALUE`, bez navodnika):

```env
ANTHROPIC_API_KEY=sk-ant-api03-...
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=...

# Email (n8n lokalni ili IMAP poller)
IMAP_HOST=imap.gmail.com
IMAP_USER=prodaja@bitlab.rs
IMAP_PASSWORD=app-password-ovdje
SMTP_HOST=smtp.gmail.com
SMTP_USER=prodaja@bitlab.rs
SMTP_PASSWORD=app-password-ovdje

# CORS — dozvoli webshop domenu
ALLOWED_ORIGINS=["https://webshop.bitlab.rs","https://www.bitlab.rs"]
```

---

## 2. MySQL → Generisanje vektorskog indeksa

Katalog se gradi iz MySQL baze webshopa. Postoje dva pristupa.

### Pristup A: Export iz phpMyAdmin (jednostavno, ručno)

1. Otvori phpMyAdmin webshopa
2. Odaberi tabelu `products` → **Export → JSON format → Go**
3. Sačuvaj kao `all-products.json`
4. Kopiraj na VPS:

```bash
scp all-products.json user@YOUR-VPS-IP:/opt/bitlab-ai-asistent/data/
```

### Pristup B: Direktna konekcija na MySQL (preporučeno za automatizaciju)

Ova skripta se spaja direktno na webshop MySQL i generiše isti JSON format kao phpMyAdmin export.

Instaliraj MySQL klijent:

```bash
pip install pymysql
```

Dodaj u `.env`:

```env
MYSQL_HOST=IP-ADRESA-WEBSHOP-SERVERA
MYSQL_PORT=3306
MYSQL_USER=webshop_user
MYSQL_PASSWORD=lozinka
MYSQL_DB=webshop_baza
```

Kreiraj skriptu `scripts/pull_from_mysql.py`:

```python
"""
Povlači tabelu 'products' direktno iz webshop MySQL baze
i upisuje data/all-products.json u istom formatu kao phpMyAdmin export.

Pokreni:
    python scripts/pull_from_mysql.py
    python scripts/embed_products.py  # zatim kao i obično
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pymysql
import pymysql.cursors
from app.config import settings


def main() -> None:
    host     = os.environ.get("MYSQL_HOST")
    port     = int(os.environ.get("MYSQL_PORT", "3306"))
    user     = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")
    db       = os.environ.get("MYSQL_DB")

    if not all([host, user, password, db]):
        print("GREŠKA: Postavi MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB u .env", file=sys.stderr)
        sys.exit(1)

    print(f"→ Spajam se na {host}:{port}/{db} ...")
    conn = pymysql.connect(
        host=host, port=port, user=user, password=password, database=db,
        cursorclass=pymysql.cursors.DictCursor, charset="utf8mb4",
    )

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products")
            rows = cur.fetchall()

    print(f"  Pronađeno {len(rows)} redova.")

    # phpMyAdmin format koji embed_products.py očekuje
    export = [{"type": "table", "name": "products", "data": rows}]

    out_path = settings.products_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(export, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"✓ Sačuvano: {out_path} ({out_path.stat().st_size / 1_048_576:.1f} MB)")
    print("\nSad pokreni: python scripts/embed_products.py")


if __name__ == "__main__":
    main()
```

> **MySQL remote pristup:** Webshop MySQL mora dozvoliti konekciju s IP adrese VPS-a. U phpMyAdmin → Privilegije → korisnik → dodaj host = VPS IP. Ili dodaj u `my.cnf`: `bind-address = 0.0.0.0`.

### Generisanje indeksa

```bash
cd /opt/bitlab-ai-asistent
source .venv/bin/activate

# Ako koristiš Pristup B (MySQL direktno):
python scripts/pull_from_mysql.py

# Generiši embedding indeks (3-5 min, skida model prvi put)
python scripts/embed_products.py
```

Provjeri da su fajlovi nastali:

```bash
ls -lh data/products.index.npz data/products.meta.json
```

---

## 3. Systemd servis (auto-start, auto-restart)

Kreiraj servis fajl:

```bash
sudo nano /etc/systemd/system/bitlab-ai.service
```

Sadržaj:

```ini
[Unit]
Description=BitLab AI Asistent (FastAPI)
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/bitlab-ai-asistent
EnvironmentFile=/opt/bitlab-ai-asistent/.env
ExecStart=/opt/bitlab-ai-asistent/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> **`--host 127.0.0.1`** — servis sluša samo lokalno; Nginx proksira spolja. Nikad ne izlaži port 8000 direktno na internet bez autentikacije.

Aktiviraj servis:

```bash
# Zamijeni YOUR_USERNAME sa tvojim korisničkim imenom (whoami)
sudo sed -i "s/YOUR_USERNAME/$(whoami)/g" /etc/systemd/system/bitlab-ai.service

sudo systemctl daemon-reload
sudo systemctl enable bitlab-ai
sudo systemctl start bitlab-ai

# Provjeri status
sudo systemctl status bitlab-ai

# Logovi u realnom vremenu
journalctl -u bitlab-ai -f
```

Test da servis radi:

```bash
curl http://127.0.0.1:8000/healthz
```

---

## 4. Nginx reverse proxy + SSL

### Instalacija

```bash
sudo apt install nginx certbot python3-certbot-nginx -y
```

### Nginx konfiguracija

```bash
sudo nano /etc/nginx/sites-available/bitlab-ai
```

Sadržaj (zamijeni `ai.bitlab.rs` sa tvojom (pod)domenom):

```nginx
server {
    listen 80;
    server_name ai.bitlab.rs;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

Aktiviraj i testuj:

```bash
sudo ln -s /etc/nginx/sites-available/bitlab-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL (HTTPS) — Let's Encrypt, besplatno

DNS zapis `ai.bitlab.rs → VPS IP` mora biti aktivan (sačekaj propagaciju, 5-30 min).

```bash
sudo certbot --nginx -d ai.bitlab.rs
```

Certbot automatski ažurira Nginx konfiguraciju i podešava auto-obnavljanje sertifikata.

Provjeri:

```bash
curl https://ai.bitlab.rs/healthz
```

### CORS update

Nakon što imaš domensko ime, ažuriraj `.env`:

```env
ALLOWED_ORIGINS=["https://webshop.bitlab.rs","https://www.bitlab.rs"]
```

Restartuj servis:

```bash
sudo systemctl restart bitlab-ai
```

### Integracija widgeta na webshop

Na webshop sajtu, ispred `</body>` taga:

```html
<script src="https://ai.bitlab.rs/public/widget.js"></script>
```

---

## 5. n8n na VPS-u (bez ngroka)

Na VPS-u više **nema potrebe za ngrok-om** — n8n direktno zove lokalni FastAPI na `http://127.0.0.1:8000`.

Postoje dva načina da pokreneš n8n lokalno na serveru.

### Opcija A: n8n cloud (najlakše — n8n cloud poziva VPS Nginx)

Ako koristiš n8n cloud account, promijeni URL u HTTP Request nodu da pokazuje na VPS domenu:

```
http://127.0.0.1:8000/api/email   ← NE (n8n cloud ne vidi tvoj 127.0.0.1)
https://ai.bitlab.rs/api/email    ← DA (n8n cloud poziva Nginx koji proxira na 8000)
```

Nema docker-a, nema instalacije. Preporučeno ako već imaš Nginx + SSL aktivan (Korak 4).

### Opcija B: n8n self-hosted (Docker Compose)

Instaliraj Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

Kreiraj `docker-compose.yml`:

```bash
mkdir -p /opt/n8n && nano /opt/n8n/docker-compose.yml
```

```yaml
services:
  n8n:
    image: n8nio/n8n
    restart: always
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://YOUR-VPS-IP:5678
      - GENERIC_TIMEZONE=Europe/Sarajevo
    volumes:
      - /opt/n8n/data:/home/node/.n8n
```

Pokreni:

```bash
cd /opt/n8n
docker compose up -d

# Provjeri
docker compose logs -f
```

n8n UI otvori u browseru: `http://YOUR-VPS-IP:5678`

U HTTP Request nodu u n8n workflow-u postavi URL:

```
http://127.0.0.1:8000/api/email
```

> **Firewall:** Ako koristiš `ufw`, dozvoli n8n port samo lokalno ili sa specifičnog IP-a:
> ```bash
> sudo ufw allow from YOUR-OFFICE-IP to any port 5678
> ```

Importuj workflow iz projekta: **New Workflow → Import from JSON → `n8n/email-autoreply.json`**

---

## 6. Automatsko osvježavanje kataloga

Kada se katalog webshopa ažurira, treba ponovo generisati indeks. Automatiziraj s cron jobom.

Kreiraj skriptu `scripts/refresh_index.sh`:

```bash
#!/bin/bash
set -e
cd /opt/bitlab-ai-asistent
source .venv/bin/activate

echo "[$(date)] Počinjem osvježavanje kataloga..."

# Pristup B (MySQL) — ako imaš direktnu konekciju:
python scripts/pull_from_mysql.py

# Alternativa — Pristup A (SCP):
# scp webshop-user@WEBSHOP-SERVER:/path/to/export.json data/all-products.json

python scripts/embed_products.py

# Restartuj servis da učita novi indeks
systemctl restart bitlab-ai
echo "[$(date)] Katalog osvježen i servis restartovan."
```

```bash
chmod +x /opt/bitlab-ai-asistent/scripts/refresh_index.sh
```

Dodaj u crontab (svaku noć u 03:00):

```bash
sudo crontab -e
```

```cron
0 3 * * * /opt/bitlab-ai-asistent/scripts/refresh_index.sh >> /var/log/bitlab-refresh.log 2>&1
```

Ručno pokretanje (test):

```bash
sudo /opt/bitlab-ai-asistent/scripts/refresh_index.sh
```

---

## 7. Monitoring i logovi

### Status servisa

```bash
sudo systemctl status bitlab-ai
```

### Logovi uživo

```bash
journalctl -u bitlab-ai -f --since "1 hour ago"
```

### Healthcheck (provjera izvana)

```bash
curl https://ai.bitlab.rs/healthz
```

Očekivani odgovor:

```json
{
  "status": "ok",
  "chat_model": "claude-haiku-4-5-20251001",
  "email_model": "claude-sonnet-4-6",
  "embed_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
  "products_index_present": true,
  "products_meta_present": true,
  "faq_present": true
}
```

### Restart servisa

```bash
sudo systemctl restart bitlab-ai
```

---

## 8. Firewall (ufw)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'   # 80 + 443
sudo ufw enable
sudo ufw status
```

Port 8000 **ne treba** biti otvoren prema van — Nginx ga proksira.

---

## 9. Česti problemi na VPS-u

**`python3 --version` vraća 3.8 ili 3.10`**  
Instaliraj Python 3.11 (deadsnakes PPA, vidi Preduslovi).

**Servis ne startuje — `products.index.npz` ne postoji`**

```bash
cd /opt/bitlab-ai-asistent && source .venv/bin/activate
python scripts/embed_products.py
sudo systemctl start bitlab-ai
```

**Nginx `502 Bad Gateway`**  
FastAPI servis nije startovao:

```bash
journalctl -u bitlab-ai -n 50 --no-pager
sudo systemctl start bitlab-ai
```

**MySQL konekcija odbijena (`Connection refused`)**  
- Provjeri `bind-address` u MySQL konfiguraciji webshop servera
- Provjeri da korisnik ima pravo pristupa s VPS IP adrese
- Provjeri firewall na webshop serveru (port 3306)

**SSL certifikat ne može se izdati**  
DNS `ai.bitlab.rs → VPS IP` mora biti aktivan. Provjeri: `nslookup ai.bitlab.rs`

**Embedding model se skida svaki put**  
Hugging Face cache je u `~/.cache/huggingface/`. Persists između restartova servisa — skida se samo jednom.

---

## 10. Redoslijed postavljanja (večeras)

1. `ssh` na VPS
2. Kloniranje + venv + `pip install` (Korak 1)
3. Popuni `.env` (API ključevi)
4. MySQL → `pull_from_mysql.py` (ili SCP JSON) → `embed_products.py`
5. Systemd servis (Korak 3) — provjeri `curl http://127.0.0.1:8000/healthz`
6. Nginx + SSL (Korak 4) — provjeri `curl https://ai.bitlab.rs/healthz`
7. CORS update u `.env` → `systemctl restart bitlab-ai`
8. n8n: Opcija A (desktop, URL = `http://localhost:8000/api/email`) ili Opcija B (Docker, URL = `http://127.0.0.1:8000/api/email`)
9. Widget `<script>` tag na webshop
10. Cron za automatsko osvježavanje (Korak 6)
