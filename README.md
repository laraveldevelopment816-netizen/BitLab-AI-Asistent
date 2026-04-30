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

### Instalacija zavisnosti

```bash
# CPU-only PyTorch (~180MB, bez CUDA) — OBAVEZNO instalirati PRVO
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Ostali paketi
pip install -e .
```

Puna lista zavisnosti je u `pyproject.toml`.

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

Za produkciju zamijeni `localhost` sa ngrok/domenом.

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

### Kako ngrok radi

```
Internet
    │
    │  https://abc123.ngrok-free.app  ← javna adresa
    ▼
┌─────────────┐
│  ngrok CDN  │  (ngrok cloud — prihvata zahtjeve izvana)
└──────┬──────┘
       │  enkriptovani tunel (agent na laptopu)
       ▼
┌──────────────────────────────────────┐
│  Tvoj laptop (WSL2)                  │
│                                      │
│  ~/bin/ngrok ──► localhost:8000      │
│                    (FastAPI server)  │
└──────────────────────────────────────┘
```

n8n je u cloudu i ne može direktno dohvatiti `localhost:8000`. ngrok pravi tunel i daje javni HTTPS URL koji n8n koristi kao webhook.

### Korak 1 — Instalacija ngrok (jednom)

**WSL2 / Linux:**

```bash
# Preuzmi binarnu datoteku
curl -L https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz -o /tmp/ngrok.tgz
tar xzf /tmp/ngrok.tgz -C /tmp

# Smjesti u ~/bin (ne treba sudo)
mkdir -p ~/bin
mv /tmp/ngrok ~/bin/ngrok

# Provjera
~/bin/ngrok version
```

**Windows (PowerShell):**

```powershell
# Opcija A — winget (preporučeno, ugrađen u Windows 10/11)
winget install ngrok.ngrok

# Opcija B — Chocolatey
choco install ngrok

# Opcija C — ručno: preuzmi .zip sa https://ngrok.com/download,
# raspakovaj ngrok.exe i dodaj folder u PATH

# Provjera
ngrok version
```

### Korak 2 — Poveži sa ngrok accountom (jednom)

Authtoken se nalazi na [dashboard.ngrok.com](https://dashboard.ngrok.com) → Your Authtoken.

**WSL2 / Linux:**

```bash
~/bin/ngrok config add-authtoken <TVOJ_AUTHTOKEN>
```

Token se čuva u `~/.config/ngrok/ngrok.yml`.

**Windows (PowerShell):**

```powershell
ngrok config add-authtoken <TVOJ_AUTHTOKEN>
```

Token se čuva u `%USERPROFILE%\AppData\Local\ngrok\ngrok.yml`.

### Korak 3 — Pokretanje tunela

Server mora biti pokrenut (`uvicorn app.main:app --reload`) pa tek onda:

**WSL2 / Linux:**

```bash
~/bin/ngrok http 8000
```

**Windows (PowerShell):**

```powershell
ngrok http 8000
```

Output koji tražiš:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000
```

Kopiraj taj `https://...` URL — koristi se u n8n (vidi ispod).

> **Napomena:** Na free tier URL se mijenja pri svakom pokretanju ngrok-a. Platni plan daje fiksnu domenu.

### Korak 4 — Postavljanje n8n

1. Registruj se na [app.n8n.cloud](https://app.n8n.cloud) (free tier, bez kartice)
2. **New Workflow → Import from JSON** → učitaj `n8n/email-autoreply.json`
3. **Credentials → New → Gmail OAuth2** → klikni `Sign in with Google` — jedan login važi i za primanje i za slanje
4. U workflow-u pronađi **HTTP Request node → URL** i zamijeni sa:
   ```
   https://abc123.ngrok-free.app/api/email
   ```
5. **Activate** workflow (toggle gornji desni ugao u n8n)
6. Test: pošalji email na Gmail adresu sa subject `Upit za SSD` — za ~60s stiže AI reply

> **Napomena:** Gmail OAuth2 zamjenjuje i IMAP i SMTP. Nema app passworda ni posebne konfiguracije mail servera.

### Fallback — IMAP poller (bez n8n)

Ako n8n cloud nije dostupan, pokreni lokalni poller direktno:

```bash
python -m app.email_poller
```

Polluje INBOX svakih 60 sekundi. Zahtijeva popunjen IMAP/SMTP blok u `.env`.

---

## 8. Troškovi

| Servis | Plan | Cijena | Za ~1.000 upita/mj |
|--------|------|--------|---------------------|
| Claude Haiku 4.5 (chat/voice) | Pay-as-you-go | $0.80/1M input tokena | ~$1.20 |
| Claude Sonnet 4.6 (email) | Pay-as-you-go | $3/1M input tokena | ~$0.60 |
| ElevenLabs (TTS) | Free tier | $0 | 10.000 znakova/mj |
| Sentence-transformers (embeddings) | Lokalno | $0 | $0 uvijek |
| n8n | Free tier | $0 | 5.000 izvršenja/mj |
| ngrok | Free tier | $0 | 1 tunel |
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

## 10. Kontakt

**BitLab d.o.o.** · Jevrejska 37, 78000 Banja Luka  
prodaja@bitlab.rs · 066 516 174 · webshop.bitlab.rs  
JIB: 4403711250001
