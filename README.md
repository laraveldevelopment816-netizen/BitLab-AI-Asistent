# BitLab AI Asistent

AI sistem za **webshop.bitlab.rs** — tri kanala, jedna baza znanja.

```
┌──────────────────────────────────────────────────────┐
│  FastAPI backend (Python, lokalno)                   │
│  /api/chat   → Chat widget + Voice mod               │
│  /api/email  → n8n webhook (email auto-reply)        │
│  /api/tts    → ElevenLabs proxy (API ključ na serveru│
│                                                      │
│  Agent loop (Claude tool use):                       │
│    search_products   — hibridna pretraga kataloga    │
│    get_faq           — dostava, garancija, B2B...    │
│    check_availability — zaliha po šifri              │
│    escalate_to_human  — Viber/email prodajnog tima   │
└──────────────────────────────────────────────────────┘
           ▲                ▲               ▲
   ┌───────┘                │               └────────────────┐
   │                        │                               │
┌──────────────┐  ┌─────────────────┐  ┌─────────────────────────┐
│ Web Widget   │  │ Voice mod        │  │ n8n Email Auto-Reply     │
│ widget.html  │  │ voice.html       │  │ IMAP → /api/email        │
│ widget.js    │  │ Web Speech STT   │  │ → AI reply → SMTP        │
└──────────────┘  │ ElevenLabs TTS   │  └─────────────────────────┘
                  └─────────────────┘

Baza znanja:
  data/products.index.npz  — 5.278 proizvoda, lokalni vektorski indeks
  data/products.meta.json  — metadata (naziv, cijena, URL, dostupnost)
  data/faq.md              — FAQ, dostava, plaćanje, garancija (ručno kurirano)
```

---

## Struktura projekta

```
bitlab-ai-asistent/
├── app/
│   ├── main.py            # FastAPI: /api/chat, /api/email, /api/tts, /healthz
│   ├── agent.py           # Claude tool-use agent loop (max 5 iteracija)
│   ├── tools.py           # 4 alata: schema + handleri + dispatcher
│   ├── rag.py             # Hibridna pretraga: BM25 (0.4) + vektor cosine (0.6)
│   ├── faq.py             # Učitava faq.md, keyword scoring po sekcijama
│   ├── system_prompts.py  # 3 system prompta: chat / voice / email
│   ├── email_poller.py    # IMAP fallback poller (rezerva za n8n)
│   └── config.py          # Pydantic Settings, čita .env
├── scripts/
│   ├── embed_products.py  # JEDNOKRATNO: generiše products.index.npz
│   └── smoke_test.py      # Provjera 4 pitanja end-to-end
├── public/
│   ├── widget.html        # Demo BitLab webshop sa embeddovanim widgetom
│   ├── widget.js          # Embeddable chat widget (poziva /api/chat)
│   └── voice.html         # Voice mod (Web Speech STT + ElevenLabs TTS)
├── n8n/
│   └── email-autoreply.json  # n8n workflow export — importuje se jednim klikom
├── evals/                 # Sesija 4
├── tests/                 # Sesija 4
├── data/
│   ├── all-products.json  # Sirovi podaci — 5.287 proizvoda (phpMyAdmin export)
│   ├── faq.md             # Ručno kurirani FAQ sa sajta
│   ├── products.index.npz # Generiše embed_products.py — NE editovati
│   └── products.meta.json # Generiše embed_products.py — NE editovati
├── .env                   # Lokalni secrets (nije u gitu)
├── .env.example           # Šablon za .env
└── pyproject.toml         # Zavisnosti projekta
```

---

## Preduslovi

| Alat | Verzija | Provjera |
|------|---------|----------|
| Python | 3.11+ | `python3 --version` |
| pip | bilo koja | `pip --version` |

Rad na **WSL2** (Windows) ili Linux/macOS terminalu.

---

## 1. Postavljanje projekta

### Kloniranje

```bash
git clone https://github.com/tvoj-username/bitlab-ai-asistent.git
cd bitlab-ai-asistent
```

### Virtuelno okruženje

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> **Windows (PowerShell — van WSL2):**
> ```powershell
> python -m venv .venv
> .\.venv\Scripts\Activate.ps1
> ```

> **⚠️ WSL2 napomena (kritično za startup brzinu):** Ako je projekat na `/mnt/c/...`
> (Windows filesystem mounted u WSL2), Python import preko 9p protokola je **5–10× sporiji**
> nego na native Linux FS. Sentence-transformers ima ~180 .py fajlova → import može trajati
> 50+ sekundi.
>
> **Rješenje:** Drži `.venv` izvan `/mnt/c`:
> ```bash
> python3 -m venv ~/.venvs/bitlab
> source ~/.venvs/bitlab/bin/activate
> # nastavi sa pip install -e . iz projekat foldera
> ```
> Kod (sa `/mnt/c`) može ostati gdje jeste — samo venv treba biti na ext4.

### Instalacija zavisnosti

```bash
# Sve odjednom: torch CPU + projekat sa pinned deps
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
```

Šta dolazi:
- **torch CPU** (~200MB) umjesto CUDA wheel-a (~1.2GB) — ne koristimo GPU.
- **sentence-transformers <4** — bez `sparse_encoder` modula koji u v5.x dodaje ~30s import.
- **faster-whisper, edge-tts** — voice mod (lazy-loaded, ne usporavaju startup).

Provjera:
```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"  # False ✓
```

> Opcionalno za pull iz MySQL baze: `pip install -e ".[mysql]"`

---

## 2. API ključevi

Kopiraj `.env.example` u `.env`:

```bash
cp .env.example .env
```

Otvori `.env` i popuni:

```env
# Obavezno — Anthropic (Claude)
# Dobiti na: console.anthropic.com → API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...

# Opciono — ElevenLabs (Voice mod)
# Dobiti na: elevenlabs.io → My Account → API Keys
ELEVENLABS_API_KEY=sk_...
# Voice Library → Add to My Voices → Copy ID
# Preporučeni glas: Lara (Croatian/BCS, mlađi ženski)
ELEVENLABS_VOICE_ID=...

# Opciono — IMAP/SMTP (rezerva za n8n, vidi Sekciju 6)
IMAP_HOST=imap.gmail.com
IMAP_USER=email@bitlab.rs
IMAP_PASSWORD=app-password-ovdje
SMTP_HOST=smtp.gmail.com
SMTP_USER=email@bitlab.rs
SMTP_PASSWORD=app-password-ovdje
```

> **Format:** koristi `=`, ne `:`. Bez navodnika oko vrijednosti.

---

## 3. Generisanje vektorske baze (jednokratno)

Ova skripta čita `data/all-products.json`, generiše embeddings lokalno (bez API troška) i upisuje `data/products.index.npz` i `data/products.meta.json`.

```bash
python scripts/embed_products.py
```

**Trajanje:** 3–5 minuta (prvi put skida ~120MB model; naredni puta ~1–2 min).  
**Provjera:** na kraju ispiše:

```
✓ Sačuvano: data/products.index.npz (7.2 MB)
✓ Sačuvano: data/products.meta.json (4.5 MB)

Gotovo. Sad možeš pokrenuti uvicorn:
    uvicorn app.main:app --reload
```

> **Napomena:** Oba `.npz` i `.meta.json` fajla su u `.gitignore`. Svaki developer pokrene skriptu jednom lokalno.

### Smart matching: `data/category_terms.json`

Mapiranje kategorija → terminima koji nisu u imenima proizvoda te kategorije. Koristi se u dva sloja:

1. **Build-time** (`embed_products.py`): prefix se ponavlja 3× u `search_text` polju → embedding razumije "laptop" iako su u imenu samo brendovi (Acer Nitro, Lenovo IdeaPad).
2. **Search-time** (`app/rag.py`): kratki upiti (npr. "laptop", "tv 50") boost-uju proizvode iz match-ed kategorije za +0.25 — sprečava da accessory-i (torbe za laptop, postolja) preuzmu top rezultate.

**Kad dodati novu kategoriju:** ako korisnici traže tip proizvoda po generičkoj riječi koja nije u imenima, dopuni `category_terms.json` i pokreni rebuild. Skripta `scripts/embed_products.py` ima ugrađen detektor — proizvodi u kategorijama gdje prva riječ imena nije konzistentna su kandidati za prefix.

---

## 4. Pokretanje servera

```bash
uvicorn app.main:app --reload
```

Server sluša na `http://localhost:8000`.

**Startup log (očekivano):**

```
INFO:     Waiting for application startup.
Loading weights: 100%|████████████| 199/199 [...]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Provjera zdravlja

```bash
curl http://localhost:8000/healthz
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

### Swagger UI (interaktivni API docs)

Otvori u browseru: `http://localhost:8000/docs`

---

## 5. Demo — tri kanala

### Chat widget

Otvori u browseru: `http://localhost:8000`  
(ili direktno: `http://localhost:8000/public/widget.html`)

Jednolinijska integracija na bilo koji sajt:

```html
<!-- Zalijepiti pred </body> tag -->
<script src="http://localhost:8000/public/widget.js"></script>
```

Za produkciju zamijeni `localhost` sa domenом (npr. `ai.bitlab.rs`).

### Voice mod

Otvori u **Chrome ili Edge** (Firefox ne podržava Web Speech API):

```
http://localhost:8000/public/voice.html
```

Klikni mikrofon → govori → AI odgovara glasom (Lara, BCS).  
TTS radi samo ako je `ELEVENLABS_API_KEY` i `ELEVENLABS_VOICE_ID` postavljen u `.env`.

### Chat API (ručni test)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Imate li SSD 1TB do 400 KM?", "channel": "chat"}'
```

**PowerShell:**

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/chat" `
  -Method POST -ContentType "application/json" `
  -Body '{"message": "Imate li SSD 1TB do 400 KM?", "channel": "chat"}'
```

### Email API (ručni test)

```bash
curl -X POST http://localhost:8000/api/email \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "kupac@example.com",
    "subject": "Upit za SSD diskove",
    "body": "Pozdrav, zanima me imate li SSD 1TB u ponudi i kolika je dostava?"
  }'
```

---

## 6. Smoke test

Provjera da sva 4 osnovna upita rade end-to-end (server mora biti pokrenut):

```bash
python scripts/smoke_test.py
```

Očekivani output:

```
BitLab smoke test → http://localhost:8000/api/chat
──────────────────────────────────────────────────
✓ [Pretraga proizvoda — SSD]
  alati: ['search_products']
  reply: Pronašao sam nekoliko SSD opcija...

✓ [FAQ — dostava]
  alati: ['get_faq']
  reply: Dostava unutar BiH...

✓ [B2B eskalacija]
  alati: ['escalate_to_human']
  reply: Naš prodajni tim će vam se javiti...

✓ [Voice kanal — gaming monitor]
  alati: ['search_products']
  reply: Imamo nekoliko gaming monitora...

──────────────────────────────────────────────────
Rezultat: 4/4
```

---

## 7. n8n Email Auto-Reply

n8n radi **lokalno** na istoj mašini kao i FastAPI server — `/api/email` nije izložen javnom internetu.

```
┌─────────────────────────────────────────────────┐
│  Tvoja mašina (laptop / VPS)                    │
│                                                 │
│  n8n (localhost:5678) ──► localhost:8000        │
│  Gmail trigger           (FastAPI /api/email)   │
└─────────────────────────────────────────────────┘
```

### Opcija A: n8n Desktop (najlakše za lokalni demo)

1. Preuzmi i instaliraj sa [n8n.io/download](https://n8n.io/download).
2. Pokreni aplikaciju → otvori `http://localhost:5678`.
3. **New Workflow → Import from JSON** → učitaj `n8n/email-autoreply.json`.
4. U **HTTP: Pitaj AI Asistenta** nodu promijeni URL na:
   ```
   http://localhost:8000/api/email
   ```
5. **Credentials → New → Gmail OAuth2** → klikni `Sign in with Google`.
6. **Activate** workflow (toggle gornji desni ugao).
7. Test: pošalji email sa subject `Upit za SSD` — za ~60s stiže AI reply.

### Opcija B: n8n Docker (preporučeno za VPS / produkciju)

```bash
docker run -d \
  --name n8n \
  --restart always \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

Otvori `http://localhost:5678` → **New Workflow → Import from JSON** → `n8n/email-autoreply.json`.

URL u HTTP Request nodu je već postavljen na `http://host.docker.internal:8000/api/email` — to je hostname koji Docker kontejner koristi za pristup hostu. **Ne mijenjaj** osim ako koristiš docker network mode=host (tada postavi `localhost`).

**Credentials → New → Gmail OAuth2** → `Sign in with Google` → **Activate** workflow.

### Fallback — IMAP poller (bez n8n)

Ako n8n nije dostupan, lokalni poller radi isti posao:

```bash
python -m app.email_poller
```

Polluje INBOX svakih 60 sekundi. Zahtijeva popunjen `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` u `.env`.

---

## 8. Troškovi

| Servis | Plan | Cijena | Za ~1.000 upita/mj |
|--------|------|--------|---------------------|
| Claude Haiku 4.5 (chat/voice) | Pay-as-you-go | $0.80/1M input tokena | ~$1.20 |
| Claude Sonnet 4.6 (email) | Pay-as-you-go | $3/1M input tokena | ~$0.60 |
| ElevenLabs (TTS) | Free tier | $0 | 10.000 znakova/mj |
| Sentence-transformers (embeddings) | Lokalno | $0 | $0 uvijek |
| n8n (lokalni Docker) | Self-hosted | $0 | bez limita |
| **Ukupno** | | | **~$2–5/mj** |

---

## 9. Česti problemi

**Server ne startuje — `products.index.npz` ne postoji**

```bash
python scripts/embed_products.py
```

**`anthropic.AuthenticationError: invalid x-api-key`**  
Provjeri `.env` — format mora biti `ANTHROPIC_API_KEY=sk-ant-...` (sa `=`, ne `:`).

**`Your credit balance is too low`**  
Dodaj kredite na [console.anthropic.com](https://console.anthropic.com) → Plans & Billing.

**TTS ne radi — `503 ElevenLabs nije konfigurisan`**  
Postavi `ELEVENLABS_API_KEY` i `ELEVENLABS_VOICE_ID` u `.env`, pa restartuj server.

**Voice HTML ne radi**  
Web Speech API podržavaju samo Chrome i Edge. Firefox nije podržan.

**`ModuleNotFoundError`**  
Virtuelno okruženje nije aktivirano:
```bash
source .venv/bin/activate   # Linux/WSL2
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
```

**Port 8000 zauzet**

```bash
# WSL2/Linux
fuser -k 8000/tcp
# Windows PowerShell
netstat -ano | findstr :8000
# pronađi PID, pa:
taskkill /F /PID <broj>
```

---

## 9.5 Logging dashboard (Sesija 8)

Zasebna React + Vite + TS aplikacija u `dashboard/` direktorijumu — prikazuje
**fine-grained AI workflow** umjesto black-box logova. Svaki request,
svaki tool call (sa `input_json`, `output_text`, latency po koraku),
ukupne tokene, cost, by-channel × by-model breakdown.

**Stranice (6):**
- **Live** — real-time stream sa polling-om 5s, fresh-row highlight
- **History** — paginated, filteri po channel/status
- **Compare** — fan-out istog upita kroz haiku + sonnet paralelno (`POST
  /api/dashboard/compare`), side-by-side rezultati sa metrikama
- **RequestDetail** — timeline svakog tool call-a u agent loop-u
- **Stats** — top-line + by-adapter (channel × model) tabela
- **Settings** — input za `DASHBOARD_API_KEY`

**Backend:** `app/server/dashboard.py` pod `/api/dashboard/` sa Bearer auth.
Storage: SQLite + SQLAlchemy async (`var/bitlab.db`), tabele `requests`
i `tool_calls`. Tracker u `agent.py` snima svaki run agent loop-a.

**Lokalno pokretanje:**
```bash
# Generiši DASHBOARD_API_KEY i dodaj u .env
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Init DB schema
python scripts/init_db.py

# Start FastAPI (port 8000)
uvicorn app.main:app --reload

# U drugom terminalu — start Vite dev server (port 5173 sa proxy na 8000)
cd dashboard && pnpm install && pnpm dev
```

Otvori `http://localhost:5173/admin/`, idi na Settings, paste-uj
`DASHBOARD_API_KEY`, save → svi tabovi rade.

**Production build:** `cd dashboard && pnpm build` → `dashboard/dist/`
(statički, servira nginx). Detalji u `deploy/README.md`.

---

## 10. Deployment na server (VPS)

> **Server-side install:** umjesto SSH iz lokalne, deploy radi Claude Code
> instanca instalirana NA samom serveru sa direktnim shell pristupom.
> Vidi **`deploy/README.md`** za kompletan checklist (uključuje TAČKA 0 —
> server već hostuje 4 druge aplikacije, treba se prilagoditi njihovim
> konvencijama prije install-a).
>
> Brzi update flow: `sudo bash scripts/deploy.sh update`.
>
> Stari vodič: `HOSTING.md` (i dalje koristan za nginx + certbot detalje).

**Preduslovi:** Ubuntu 22.04+, Python 3.11+, 1 GB RAM, domena usmjerena na VPS IP.

### Korak 1 — Kloniranje i okruženje

```bash
ssh user@YOUR-VPS-IP

cd /opt
sudo git clone https://github.com/tvoj-username/bitlab-ai-asistent.git
sudo chown -R $USER:$USER /opt/bitlab-ai-asistent
cd /opt/bitlab-ai-asistent

python3.11 -m venv .venv
source .venv/bin/activate
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
```

### Korak 2 — Konfiguracija

```bash
cp .env.example .env
nano .env   # popuni ANTHROPIC_API_KEY, ELEVENLABS_*, IMAP/SMTP, ALLOWED_ORIGINS
```

### Korak 3 — Generisanje indeksa

```bash
# Kopiraj data/all-products.json na server, pa:
python scripts/embed_products.py
ls -lh data/products.index.npz data/products.meta.json  # provjera
```

### Korak 4 — Systemd servis

```bash
sudo nano /etc/systemd/system/bitlab-ai.service
```

```ini
[Unit]
Description=BitLab AI Asistent
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/opt/bitlab-ai-asistent
EnvironmentFile=/opt/bitlab-ai-asistent/.env
ExecStart=/opt/bitlab-ai-asistent/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo sed -i "s/YOUR_USERNAME/$(whoami)/g" /etc/systemd/system/bitlab-ai.service
sudo systemctl daemon-reload
sudo systemctl enable --now bitlab-ai
curl http://127.0.0.1:8000/healthz   # provjera
```

### Korak 5 — Nginx + SSL

```bash
sudo apt install nginx certbot python3-certbot-nginx -y

# Konfiguracija (zamijeni ai.bitlab.rs)
sudo tee /etc/nginx/sites-available/bitlab-ai <<'EOF'
server {
    listen 80;
    server_name ai.bitlab.rs;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/bitlab-ai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# SSL — DNS mora biti aktivan (sačekaj 5-30 min propagaciju)
sudo certbot --nginx -d ai.bitlab.rs
curl https://ai.bitlab.rs/healthz   # provjera
```

### Korak 6 — n8n (email auto-reply)

**Docker (preporučeno):**

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

docker run -d \
  --name n8n \
  --restart always \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

Otvori `http://YOUR-VPS-IP:5678` → **New Workflow → Import from JSON** → `n8n/email-autoreply.json`.

URL u HTTP Request nodu postavi na:
```
http://127.0.0.1:8000/api/email
```

**Credentials → Gmail OAuth2 → Sign in with Google → Activate workflow.**

> Firewall: `sudo ufw allow from YOUR-OFFICE-IP to any port 5678` — n8n UI ne treba biti javno dostupan.

### Korak 7 — Widget na webshop

```html
<!-- Dodati pred </body> na webshop sajtu -->
<script src="https://ai.bitlab.rs/public/widget.js"></script>
```

### Korak 8 — Auto-osvježavanje kataloga (cron, noću)

```bash
sudo crontab -e
# Dodaj:
0 3 * * * /opt/bitlab-ai-asistent/scripts/refresh_index.sh >> /var/log/bitlab-refresh.log 2>&1
```

---

## 11. Kontakt

**BitLab d.o.o.** · Jevrejska 37, 78000 Banja Luka  
prodaja@bitlab.rs · 066 516 174 · webshop.bitlab.rs  
JIB: 4403711250001
