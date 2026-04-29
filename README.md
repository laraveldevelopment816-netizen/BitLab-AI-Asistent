# BitLab AI Asistent

Kompletan AI sistem za **webshop.bitlab.rs** — tri kanala, jedna baza znanja, produkcijski spreman.

```
┌─────────────────────────────────────┐
│   Backend (Node.js, Express)        │
│   - /api/chat   (widget + voice)    │
│   - /api/email  (n8n webhook)       │
│   - /api/tts    (ElevenLabs proxy)  │
│                                     │
│   Agent loop (Claude Haiku):        │
│   tools = [                         │
│     search_products,                │
│     get_faq,                        │
│     check_availability,             │
│     escalate_to_human               │
│   ]                                 │
└─────────────────────────────────────┘
            ▲         ▲          ▲
  ┌─────────┘         │          └──────────────┐
  │                   │                         │
┌────────────┐ ┌─────────────┐  ┌──────────────────────┐
│ Web Widget │ │ Voice HTML  │  │ n8n Email Auto-Reply  │
│ (na sajtu) │ │ (BCS TTS)   │  │ Gmail → API → Reply   │
└────────────┘ └─────────────┘  └──────────────────────┘

Knowledge base:
  products.index.json  — 5.287 proizvoda + embeddings (lokalni vector store)
  data/faq.md          — FAQ, dostava, plaćanje, garancija (ručno kurirano)
```

---

## Struktura projekta

```
bitlab-ai-asistent/
├── server.js                  # Express backend, svi API endpointi
├── package.json
├── .env.example               # Šablon za env varijable
├── lib/
│   ├── agent.js               # Claude tool-use agent loop
│   ├── tools.js               # Definicije i handleri alata
│   ├── rag.js                 # Cosine similarity nad products.index.json
│   ├── faq.js                 # FAQ pretraga
│   └── system-prompt.md       # Jedan system prompt za sva tri kanala
├── public/
│   ├── widget.html            # Embeddable chat widget
│   └── voice.html             # Voice mode (Web Speech + ElevenLabs)
├── scripts/
│   └── embed_products.py      # Generiše products.index.json (jednokratno)
├── data/
│   ├── all-products.json      # Sirovi podaci — 5.287 proizvoda
│   ├── faq.md                 # Ručno kurirani FAQ sa sajta
│   └── products.index.json    # Generisano skriptom — NE editovati ručno
├── n8n/
│   └── email-autoreply.json   # n8n workflow export, importuje se klikom
├── evals/
│   ├── test-questions.json    # 15–20 realnih pitanja sa očekivanim alatom
│   └── run.js                 # Pokreće evaluaciju, ispisuje pass/fail tabelu
└── README.md
```

---

## Preduslovi

| Alat | Minimalna verzija | Provjera |
|------|-------------------|----------|
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Git | bilo koja | `git --version` |

---

## Postavljanje projekta

### 1. Kloniranje repozitorija

```bash
git clone https://github.com/vas-username/bitlab-ai-asistent.git
cd bitlab-ai-asistent
```

### 2. API ključevi — pribaviti PRIJE nastavka

Trebate 4 ključa:

| Servis | Gdje se dobija | Varijabla u .env |
|--------|----------------|------------------|
| Anthropic (Claude) | console.anthropic.com → API Keys | `ANTHROPIC_API_KEY` |
| OpenAI (embeddings) | platform.openai.com/api-keys | `OPENAI_API_KEY` |
| ElevenLabs (TTS) | elevenlabs.io → My Account → API Keys | `ELEVENLABS_API_KEY` |
| ElevenLabs Voice ID | elevenlabs.io → Voices → (...) → Copy ID | `ELEVENLABS_VOICE_ID` |

### 3. Kreiranje .env fajla

```bash
# Linux / macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Otvorite `.env` u editoru i popunite vrijednosti:

```env
# Claude API (agent loop)
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI (samo za generisanje embeddings — jednokratno)
OPENAI_API_KEY=sk-...

# ElevenLabs (TTS proxy)
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Server
PORT=3000
NODE_ENV=development
```

---

## Instalacija — Node.js backend

### Linux / macOS

```bash
npm install
```

### Windows (PowerShell ili CMD)

```powershell
npm install
```

Ako dobijete grešku vezanu za `node-gyp` na Windowsu:

```powershell
npm install --ignore-scripts
```

---

## Generisanje vektorske baze (jednokratno)

Ova skripta čita `data/all-products.json`, šalje svaki proizvod na OpenAI Embeddings API i upisuje rezultat u `data/products.index.json`.

**Troškovi:** ~$0.10 za 5.287 proizvoda (text-embedding-3-small, $0.02/1M tokena).
**Trajanje:** 3–5 minuta (API rate limiting).

### Linux / macOS — Python venv

```bash
# Kreiraj virtualno okruženje
python3 -m venv venv

# Aktiviraj
source venv/bin/activate

# Instaliraj pakete
pip install openai python-dotenv tqdm

# Pokreni skriptu
python scripts/embed_products.py

# Deaktiviraj kad završiš
deactivate
```

### Windows — Python venv (PowerShell)

```powershell
# Kreiraj virtualno okruženje
python -m venv venv

# Aktiviraj (PowerShell)
.\venv\Scripts\Activate.ps1

# Ako dobijete grešku oko execution policy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Zatim ponovo:
.\venv\Scripts\Activate.ps1

# Instaliraj pakete
pip install openai python-dotenv tqdm

# Pokreni skriptu
python scripts\embed_products.py

# Deaktiviraj kad završiš
deactivate
```

### Windows — Python venv (CMD)

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install openai python-dotenv tqdm
python scripts\embed_products.py
deactivate
```

**Očekivani output:**

```
Učitavam all-products.json... 5287 proizvoda
Generišem embeddings: 100%|████████████████| 5287/5287 [03:42<00:00, 23.8it/s]
Upisujem products.index.json...
✓ Gotovo. 5287 embeddings sačuvano u data/products.index.json
```

> **Napomena:** `data/products.index.json` se ne commituje u Git (dodat u `.gitignore`) jer je ~32 MB.  
> Svaki developer pokrene skriptu lokalno jednom.

---

## Pokretanje backend servera

### Razvojni mod (s auto-reloadom)

```bash
# Linux / macOS
npm run dev

# Windows
npm run dev
```

### Produkcijski mod

```bash
# Linux / macOS
npm start

# Windows
npm start
```

Server sluša na `http://localhost:3000`.

**Provjera da radi:**

```bash
# Linux / macOS
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Imate li SSD 1TB?"}'

# Windows (PowerShell)
Invoke-RestMethod -Uri "http://localhost:3000/api/chat" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"message": "Imate li SSD 1TB?"}'
```

---

## Pokretanje evaluacija

Evaluacija pokreće 15–20 realnih pitanja kroz agenta i mjeri koliko alata agent ispravno poziva.

```bash
# Linux / macOS / Windows
node evals/run.js
```

**Očekivani output:**

```
┌─────────────────────────────────────────────┬──────────────────┬────────┐
│ Pitanje                                     │ Očekivani alat   │ Status │
├─────────────────────────────────────────────┼──────────────────┼────────┤
│ Imate li SSD 1TB do 200KM?                  │ search_products  │ ✓ PASS │
│ Dostavljate li u Mostar?                    │ get_faq          │ ✓ PASS │
│ Trebam ponudu za firmu, JIB 123456789       │ escalate_to_human│ ✓ PASS │
│ ...                                         │ ...              │ ...    │
└─────────────────────────────────────────────┴──────────────────┴────────┘
Rezultat: 18/20 pitanja prošlo (90%)
```

---

## Web widget — integracija na sajt

Otvorite `public/widget.html` u browseru direktno, ili embed-ujte na postojeći sajt jednim blokom:

```html
<!-- Zalijepiti pred </body> tag -->
<script src="https://vasa-domena.com/widget.js"></script>
```

Widget poziva `POST /api/chat` — API ključ je na serveru, ne u HTML-u.

---

## Voice mode

Otvorite `public/voice.html` u **Chrome ili Edge** browseru (Firefox ne podržava Web Speech API).

```bash
# Linux / macOS — direktno otvaranje
google-chrome public/voice.html
# ili
open public/voice.html   # macOS

# Windows
start public\voice.html
```

Ili posjetite `http://localhost:3000/voice.html` dok server radi.

---

## n8n Email Auto-Reply

1. Registrujte se na [n8n.io](https://n8n.io) (free tier, bez kartice)
2. Kreirajte novi workflow → Import from JSON
3. Učitajte `n8n/email-autoreply.json`
4. U HTTP Request node-u zamijenite `YOUR_SERVER_URL` sa vašim deploy URL-om
5. Konfigurirajte Gmail / IMAP credential u Trigger node-u
6. Toggle **Active → ON**

Workflow:
```
Gmail Trigger → IF (subject contains upit/ponuda/cijena/dostava) 
  → POST /api/email → Gmail Reply → Slack notif
```

---

## Deploy (produkcija)

### Render.com (preporučeno — besplatno)

1. Push kod na GitHub
2. Idite na [render.com](https://render.com) → New → Web Service
3. Povežite GitHub repo
4. Postavke:
   - **Build Command:** `npm install`
   - **Start Command:** `npm start`
   - **Environment:** Node
5. Environment Variables: dodajte sve iz `.env`
6. Klik **Create Web Service**

Deploy traje 2–3 minute. Dobijete URL kao `https://bitlab-ai.onrender.com`.

> **Napomena:** Na Render free tier, `products.index.json` mora biti commitovan ili generisan u build fazi. Dodajte u Build Command:  
> `npm install && pip install openai python-dotenv && python scripts/embed_products.py`

### Vercel (alternativa — za serverless)

```bash
npm i -g vercel
vercel --prod
```

---

## Troškovi u produkciji

| Servis | Plan | Cijena | Za 1.000 pitanja/mj |
|--------|------|--------|---------------------|
| Claude Haiku 4.5 | Pay-as-you-go | $0.80/1M input tokena | ~$1.20 |
| Claude Sonnet (email) | Pay-as-you-go | $3/1M input tokena | ~$0.90 |
| ElevenLabs | Starter | $5/mj | 30.000 karaktera |
| OpenAI embeddings | Pay-as-you-go | $0.02/1M tokena | jednokratno ~$0.10 |
| Render hosting | Free | $0 | — |
| n8n | Free tier | $0 | 5.000 izvršenja/mj |
| **Ukupno** | | | **~$7–12/mj** |

**ROI:** 70%+ pitanja AI rješava sam = ~5 sati sedmično ušteđenih za vlasnika.

---

## Česti problemi

**`ECONNREFUSED` pri pozivu /api/chat**
Server nije pokrenut. Pokrenite `npm run dev` u zasebnom terminalu.

**`Invalid API key` u evaluacijama**
Provjerite `.env` — bez razmaka oko `=`, bez navodnika oko vrijednosti.

**Python skripta: `ModuleNotFoundError: No module named 'openai'`**
Virtualnog okruženja nije aktivirano. Pokrenite `source venv/bin/activate` (Linux) ili `.\venv\Scripts\Activate.ps1` (Windows) pa opet `pip install`.

**ElevenLabs: `401 Unauthorized`**
API ključ počinje sa `sk_`, ne `sk-`. Provjerite na elevenlabs.io → My Account → API Keys.

**Voice HTML ne radi u Firefoxu**
Web Speech API podržavaju samo Chrome i Edge. Prebacite browser.

**`products.index.json` ne postoji — server ne startuje**
Potrebno je pokrenuti Python skriptu (vidi sekciju "Generisanje vektorske baze").

---

## Kontakt i autori

**Projekat:** AI Forward Faza 2 — BitLab AI Asistent  
**Partneri:** ICBL Banja Luka + Bloomteq  
**Predavač:** Đuro Grubišić