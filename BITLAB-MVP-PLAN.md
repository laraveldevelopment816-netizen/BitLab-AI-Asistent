# BitLab AI Asistent — MVP Plan (Python lokalno)

> **Cilj:** Izdvojiti se od ~10 učesnika i ući u uži izbor za angažman.
> **Pristup:** Sve u Pythonu, sve lokalno, sve zatvoreno-zavisno (no OpenAI, no Vercel).
> **Datum:** 2026-04-29.
> **Postojeća priprema:** `data/faq.md` ✓, `data/all-products.json` (5.287 proizvoda) ✓.

---

## 1. Promjene u odnosu na prvu verziju plana

| Stavka | Prije | Sada |
|---|---|---|
| Backend jezik | Node.js | **Python (FastAPI)** |
| Hosting | Render free | **Lokalno** (uvijek pokrenuto na laptopu za demo); n8n zove `localhost`/ngrok |
| Embeddings | OpenAI `text-embedding-3-small` | **Lokalni `sentence-transformers`** (multilingual, BCS, offline, 0 troška) |
| Email trigger | Gmail OAuth | **IMAP** (potvrda korisnika) |
| Vector store | Supabase | **Lokalni `products.index.npz`** (numpy) |
| FAQ | Treba kopirati | **Već postoji** (`data/faq.md`, 125 linija) |
| GPT-5 fallback | — | **Copilot CLI** ako Claude prozor presahne |

---

## 2. Tech stack (finalni)

| Sloj | Tehnologija | Razlog |
|---|---|---|
| Web framework | **FastAPI** + uvicorn | async, jednostavan, ugrađen Swagger UI za demo |
| LLM | **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) za chat/voice; **Sonnet 4.6** za email auto-reply | Brzina + cijena za realtime, kvalitet za pisani tekst |
| Embeddings | **`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`** | Radi BCS, lokalno, ~120MB, 0 API troška |
| Vector search | **`numpy` cosine** + opcionalno **`rank-bm25`** za hibrid | 5.287 vektora x 384 dim ≈ 8MB — trivijalno za in-memory |
| TTS | **ElevenLabs** (Multilingual v2, glas Lara) | Native BCS, kako kursni materijal preporučuje |
| STT | **Web Speech API** (browser) | Besplatno u Chrome/Edge, dovoljno za demo |
| Email | **`imaplib`** + `email` (stdlib) | IMAP poll, nema OAuth komplikacija |
| Automatizacija | **n8n cloud (free tier)** sa HTTP Request → naš `/api/email` | Diferencijator |
| Tunneling | **`ngrok`** ili **Cloudflare Tunnel** | n8n cloud mora dosegnuti naš lokalni server |
| Frontend widget | Vanilla JS, jedan HTML fajl | Embeddable, lagano |
| Testovi | **`pytest`** + custom `evals/run.py` | Pokazuje inženjerski pristup |

---

## 3. Struktura projekta

```
bitlab-ai-asistent/
├── app/
│   ├── main.py                # FastAPI: /api/chat, /api/email, /api/tts, /healthz
│   ├── agent.py               # Agent loop sa Claude tool use
│   ├── tools.py               # search_products, get_faq, check_availability, escalate
│   ├── rag.py                 # Učitava index, cosine search, opciono BM25 hibrid
│   ├── faq.py                 # Učitava data/faq.md, sekcijska pretraga
│   ├── email_poller.py        # IMAP background task, fillter subject, poziva agent
│   ├── system_prompts.py      # 3 prompt-a (chat / voice / email) iz jednog osnovnog
│   └── config.py              # env loader (Pydantic settings)
├── scripts/
│   ├── embed_products.py      # JEDNOKRATNO: čita all-products.json, pravi index.npz
│   └── smoke_test.py          # Curl-style provjera svih endpointa
├── public/
│   ├── widget.html            # Embeddable chat widget (BitLab brending)
│   ├── widget.js              # Logika widgeta (poziva /api/chat)
│   └── voice.html             # Voice mod (Web Speech STT + ElevenLabs TTS)
├── n8n/
│   └── email-autoreply.json   # n8n workflow export (importuje se klikom)
├── evals/
│   ├── test_questions.json    # 18–20 realnih pitanja sa očekivanim alatom
│   └── run.py                 # Pokrene sve, ispiše pass/fail tabelu
├── data/
│   ├── all-products.json      # ✓ postoji
│   ├── faq.md                 # ✓ postoji (125 linija)
│   └── products.index.npz     # generiše scripts/embed_products.py
├── tests/
│   └── test_tools.py          # pytest unit testovi za alate
├── .env.example
├── .gitignore
├── pyproject.toml             # ili requirements.txt
├── README.md
└── BITLAB-MVP-PLAN.md         # ovaj fajl
```

---

## 4. Sesije rada — koji model, koji effort, koji posao

> **Princip:** Opus radi tamo gdje je razmišljanje skupo (arhitektura, prompt engineering, security/eval review). Sonnet radi obim posla. Effort se diže samo gdje stvarno donosi razliku — inače se troši nepotrebno.

### 🟢 Sesija 0 — Priprema (van Claude Code, **0 tokena**) — ✅ ZAVRŠENO

Ručni rad **prije** prve sesije. Cilj: ući u sesiju sa svim ključevima, nalozima i indeksom već gotovim.

- [ ] Anthropic API ključ u `.env` (`ANTHROPIC_API_KEY`)
- [ ] ElevenLabs nalog + Voice ID za **Lara** glas
- [ ] n8n cloud free nalog (workspace npr. `bitlab-ai`)
- [ ] `ngrok` nalog (free) za tunneling
- [ ] IMAP nalog za testne emailove (može Gmail sa app-password ili Mailtrap)
- [ ] Python 3.11+ venv: `python -m venv .venv && source .venv/bin/activate`
- [ ] `pip install fastapi uvicorn anthropic sentence-transformers numpy python-dotenv pydantic-settings rank-bm25 imaplib2`
- [ ] Pokrenuti **lokalno** `scripts/embed_products.py` da se napravi `data/products.index.npz`
  - Čita `all-products.json`, izvuče `id, name, description, price, kolicina, urlhash`, sklopi tekst, embeduje sve, sačuva kao npz (vektori) + json (metadata).
  - Ovo radi sa modelom koji se prvi put download-uje (~2 minuta), pa traje ~3–5 minuta na CPU-u.
  - **Ova skripta je već definisana u Sesiji 1, ali se POKREĆE lokalno između sesija** da Claude Code ne troši tokene gledajući 5.287 redova.
- [ ] BitLab brand boje: orange `#FB923C` (iz demo widget-a), tamno plava `#0F2A47` — već znamo
- [ ] Brand asset: SVG/PNG logoa BitLab-a u `public/assets/`

**Rezultat sesije 0:** Sve eksternoe zavisnosti spremne. Sesija 1 može krenuti čisto u kod.

---

### 🟡 Sesija 1 — Arhitektura, skelet, sistem prompt — ✅ ZAVRŠENO
**Model: Opus 4.7 sa visokim effortom**
**Procjena: ~25k input / 12k output tokena**

Opus jer ovdje su odluke najskuplje da se isprave kasnije: shape API-ja, oblik tool-ova, sadržaj system prompta, format index-a.

**Šta se radi:**

1. `/plan` mode prvih 5 minuta — fiksiramo svaki fajl iz strukture iznad, signature funkcija, format `products.index.npz` i pratećeg metadata JSON-a.
2. Napiše `app/config.py`, `app/main.py` (samo skeleton sa endpoint placeholder-ima), `pyproject.toml`, `.env.example`, `.gitignore`.
3. Napiše `scripts/embed_products.py` — kompletan, izvršiv. (Korisnik ga pokreće lokalno između sesija da popuni `products.index.npz`.)
4. Napiše `app/system_prompts.py` — **OVO JE KRITIČNO**, Opus radi prompt engineering:
   - Bazni BitLab prompt (firma, kontakti, ton, jezik, obavezno spominjanje da se eskalira na Viber/email kad ne zna)
   - 3 varijante: `CHAT`, `VOICE` (kraće, izgovorno), `EMAIL` (formalnije, sa potpisom)
5. Definiše tool schema u `app/tools.py` (samo JSON definicije, ne implementacije još).
6. Napiše `app/faq.py` — učitava `data/faq.md`, parsira po `##` headerima u sekcije.

**Šta NE radi:** RAG implementacija, agent loop, frontend, evali.

**Izlaz iz sesije 1:** projekat se može `pip install -e .` instalirati i uvicorn pokrenuti, endpointi vraćaju 501 Not Implemented, ali skripta za embedding radi.

**Između sesije 1 i 2 (van Claude Code):** Pokrenuti `python scripts/embed_products.py`. Provjeriti da `data/products.index.npz` postoji.

---

### 🔵 Sesija 2 — Agent loop, alati, RAG — ✅ ZAVRŠENO
**Model: Sonnet 4.6 sa visokim effortom**
**Procjena: ~30k input / 20k output tokena**

Najveći blok obima posla. Sonnet je tu jer Opus ne donosi dovoljnu razliku za standardnu Python implementaciju, ali high effort je dobar jer agent loop + tool use dispatch može imati suptilne bugove.

**Šta se radi:**

1. `app/rag.py` — učita `products.index.npz`, implementira `search(query, top_k=5)` koristeći cosine similarity. Hibrid: BM25 nad imenima/keywordsima + vektorska pretraga, score fusion (weighted sum 0.4 BM25 + 0.6 vector).
2. `app/tools.py` — implementirati 4 tool handlera:
   - `search_products(query, top_k=5, max_price=None)` → vraća listu `{name, price, availability, url}`
   - `get_faq(topic)` → fuzzy match nad sekcijama iz `faq.py`
   - `check_availability(product_id_or_sifra)` → čita iz JSON-a, gleda `kolicina`, `ProductAvailability`, `dobavljivost`
   - `escalate_to_human(reason, summary)` → vraća strukturni odgovor sa kontaktima
3. `app/agent.py` — agent loop:
   - Prima `messages`, `channel` (chat/voice/email)
   - Bira system prompt po channel-u
   - Petlja: `client.messages.create(tools=...)` → ako `stop_reason == "tool_use"`, izvrši alat, dodaj rezultat, ponovi (max 5 iteracija)
   - Vraća konačni tekst + lista korištenih alata (za debug i evale)
4. `app/main.py` — implementirati `/api/chat` (POST `{message, history, channel}` → `{reply, tools_used}`)
5. **Smoke test:** `python scripts/smoke_test.py` provjerava 3–4 pitanja end-to-end.

**Šta NE radi:** voice, email, frontend, n8n, evali.

**Izlaz iz sesije 2:** Backend radi za chat. Pitanje "Imaš li SSD do 200KM?" vraća listu proizvoda iz pravog kataloga.

---

### 🟣 Sesija 3 — Kanali (widget + voice + email + n8n) — ✅ ZAVRŠENO
**Model: Sonnet 4.6 sa srednjim effortom**
**Procjena: ~25k input / 15k output tokena**

Ovo je više "pisanje fajlova po šablonu" nego razmišljanje, pa srednji effort. Frontend kod (HTML/JS) i n8n JSON imaju jasnu formu.

**Šta se radi:**

1. `public/widget.html` + `public/widget.js`:
   - Plutajući launcher u uglu, BitLab branding
   - Tipping indicator, Markdown render (linkovi do proizvoda)
   - Mobile responsive
   - `<script src="http://localhost:8000/widget.js"></script>` jednolinijska integracija
2. `public/voice.html`:
   - Adaptacija `docs/dan4/demo_voice_v2.html` da zove naš `/api/chat` (channel=voice)
   - TTS preko našeg `/api/tts` endpointa (proxy ka ElevenLabs)
3. `app/main.py`: dodati `/api/tts` (POST `{text, voice_id}` → audio stream), `/api/email` (POST `{from, subject, body}` → `{reply, escalated: bool}`)
4. `app/email_poller.py` — opcionalan IMAP poller (za demo radimo n8n verziju, ovo je rezerva ako n8n cloud zataji):
   - Konektuje se na IMAP, polluje every 60s, za nove mailove sa subject keywordima zove agent, šalje SMTP reply
5. `n8n/email-autoreply.json`:
   - Trigger: IMAP Email node (n8n ima native IMAP node — bez OAuth)
   - IF: subject contains `upit|ponuda|cijena|dostava|garancija|kako|imate li`
   - HTTP Request: POST na `https://<ngrok>/api/email` sa `{from, subject, body}`
   - Send Email node: reply na `from` sa AI odgovorom
   - **Eksportujem JSON, korisnik importuje klikom u n8n UI** (ne troši sesijske tokene na klikanje).

**Šta NE radi:** evali, README, polish.

**Izlaz iz sesije 3:** Sva tri kanala rade. Demo flow je moguć end-to-end.

---

### 🟠 Sesija 4 — Evali + polish + security review — ✅ ZAVRŠENO
**Početak: Sonnet 4.6 srednji effort. Završetak: Opus 4.7 visoki effort za review.**
**Procjena: ~20k input / 12k output tokena**

**Status (2026-05-01):** Tačke 1–4 (evali, README, unit testovi) završene. Tačka 5 (security
review) završena — vidi `SECURITY-REVIEW.md`. Otvorene stavke (V2, V3, S1–S3, N2, N3)
prebačene u Sesiju 7.

**Sonnet dio:**

1. `evals/test_questions.json` — 18 realnih pitanja:
   ```json
   [
     {"q": "Imate li SSD 1TB?", "expect_tool": "search_products", "expect_contains": ["SSD"]},
     {"q": "Dostavljate li u Mostar?", "expect_tool": "get_faq"},
     {"q": "Treba mi ponuda za firmu sa JIB-om", "expect_tool": "escalate_to_human"},
     ...
   ]
   ```
2. `evals/run.py` — pokreće sva pitanja kroz agent, ispisuje tabelu (q | tool used | pass/fail | latency).
3. `tests/test_tools.py` — 4–5 unit testova za alate (search, faq, availability).
4. README.md sa: arhitektura (ASCII slika iz ovog plana), kako pokrenuti, cijene, ROI.

**Opus dio (na kraju):**

5. **Security + kvalitet review** sa Opus 4.7 high effort:
   - Procuri li API ključ negdje? (Treba biti samo backend.)
   - Šta agent radi na "ignoriši prethodne instrukcije" (prompt injection)?
   - Šta ako search ne nađe ništa — escallira li?
   - Da li email-system-prompt potpisuje BitLab-om?
   - Pregled `system_prompts.py` — popravljanje halucinacija.

**Izlaz iz sesije 4:** Eval skor (cilj: 16/18+), README sa pitch sekcijom, security clean.

---

### ⚪ Sesija 5 — Demo prep i pitch (opciono, ako ostane vremena/tokena) — ✅ ZAVRŠENO
**Model: Sonnet 4.6 sa niskim effortom (ili bez thinking-a)**
**Procjena: ~8k input / 6k output tokena**

1. Skript za demo (90 sekundi):
   - Otvori widget na lokalnom testnom sajtu
   - Postavi 2 chat pitanja (jedno proizvod, jedno FAQ)
   - Prebaci na voice mod, postavi 1 glasovno pitanje
   - Pošalji email na test inbox, čekaj automatski reply
   - Pokaži `evals/run.py` rezultat
2. README "Pitch" sekcija — bullet point iz plana sekcije 8.
3. Opciono: kratak Loom snimak (radim van Claude Code-a).

---

### 🔴 Sesija 6 — Migracija n8n na lokalni hosting (ngrok out)
**Model: Sonnet 4.6 sa srednjim effortom**
**Procjena: ~10k input / 6k output tokena**

Cilj: skinuti `/api/email` sa javnog interneta. Time se zatvara security nalaz **V1**
iz `SECURITY-REVIEW.md` (otvoren `/api/email` bez auth-a). Ngrok cloud tunel se uklanja.

**Šta se radi:**

1. **n8n lokalno (Docker ili desktop):**
   - `docker run -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n` — radi na `localhost:5678`.
   - Importovati postojeći `n8n/email-autoreply.json`.
   - Promijeniti URL u **HTTP Request** node-u sa `https://bonsai-census-daisy.ngrok-free.dev/api/email`
     na `http://host.docker.internal:8000/api/email` (Docker) ili `http://localhost:8000/api/email`
     (desktop n8n).
   - IMAP/Gmail trigger ostaje isti — samo n8n→backend leg ide preko lokalne mreže.
2. **Update `n8n/email-autoreply.json`** — eksport sa novim URL-om i commit.
3. **Update `HOSTING.md`** — sekcija "n8n cloud + ngrok" se mijenja u "n8n lokalno (Docker)";
   uputstvo kako se podiže prvi put.
4. **Provjera demo flow-a:**
   - Pošalji testni email → n8n trigger → POST na `localhost:8000/api/email` → SMTP reply.
   - Provjeriti da Gmail OAuth credentials u n8n-u i dalje rade nakon migracije.
5. **Ukloniti ngrok** iz `.env.example`, `HOSTING.md`, README-a (ako se igdje pominje).

**Šta NE radi:** ne dirati `/api/email` Pydantic schema, ne uvoditi shared-secret header
(nije više potrebno jer endpoint nije izložen javnom internetu).

**Izlaz iz sesije 6:** `/api/email` više nije javno dostupan. n8n radi lokalno. Demo flow
end-to-end potvrđen.

---

### 🟤 Sesija 7 — Quality polish: search, STT, deps, prompt review, security backlog
**Mješoviti model — vidi raspodjelu po podzadatku.**
**Procjena: ~45k input / 25k output tokena (ukupno za sve podzadatke)**

Cilj: zatvoriti **sve preostale stavke iz `SECURITY-REVIEW.md`** + popraviti nekoliko
funkcionalnih bolnih tačaka koje su se pojavile tokom testiranja MVP-a:

- Search ne nalazi laptopove jer su u bazi indeksirani kao "notebook" / model-serije.
- Server se diže ~1 minut (sentence-transformers + faster-whisper povlače `torch` sa
  CUDA wheelovima koji nam ne trebaju, traje import).
- Groq Whisper (cloud STT) maši riječi — vraćamo se na lokalni `faster-whisper`
  ili tražimo bolju alternativu.
- Haiku 4.5 ponekad daje čudna objašnjenja u chat odgovoru — prompt polish.
- Voice flow "naruči" → mailto link radi, ali treba dotjerati cross-channel cycle.

**Princip raspodjele modela (token štednja, imamo do sutra):**
> Opus radi tamo gdje je pogrešna odluka skupa da se ispravi (algoritmi, prompt
> engineering, prompt review). Sonnet radi obim koda i config-a. Haiku samo za
> mehanički rad ako se pojavi.

#### 7.1 Smart product matching — laptop ↔ notebook problem — ✅ ZAVRŠENO
**Model: Opus 4.7 high effort** (~6k in / 4k out)

Trenutno `tools.py:13` ima hardkodiranu regex listu serija (`ideapad|thinkbook|...`).
Ne skalira. Treba pametniji pristup:

- **Opcija A (preporučena):** generisati synonym/category dictionary **iz baze** pri
  build-u indeksa. `scripts/embed_products.py` već čita `all-products.json` — proširiti
  ga da ekstraktuje kategorije i top-K riječi po kategoriji u `data/category_terms.json`.
  Pri search-u, ako query sadrži generičku riječ ("laptop", "tastatura", "monitor"),
  query expansion dodaje stvarne termine iz baze.
- **Opcija B:** koristiti BM25 + vektor weighting drugačije — ako BM25 vrati 0 hitova,
  povući top-1 vektorski rezultat i njegovu kategoriju, pa re-search-ovati po kategoriji.
- Opus odlučuje između A/B na osnovu strukture `all-products.json`.

Plus: zatvara nalaz **S3** (eskalacija pri praznom search-u) — ako oba pokušaja vrate
prazno, eskalira.

#### 7.2 CPU-only deps — brži startup — ✅ ZAVRŠENO
**Model: Sonnet 4.6 medium effort** (~4k in / 3k out)
**Rezultat:** startup pao sa **60s na 2.7s**. Lazy import + bg preload + ST<4 pin + WSL2 napomena u README.

`sentence-transformers` i `faster-whisper` povlače full PyTorch wheel (~2GB sa CUDA).
Mi smo na CPU-u — prepolovljava se memorija i import vrijeme ako se eksplicitno
instalira CPU-only torch.

**Šta se radi:**
1. Update `pyproject.toml` — odvojiti optional dependencies:
   ```toml
   [project.optional-dependencies]
   cpu = [
     "torch==2.5.1+cpu ; platform_system != 'Darwin'",
     "torch==2.5.1 ; platform_system == 'Darwin'",
     "faster-whisper>=1.1",
     "edge-tts>=7.0",
   ]
   ```
2. Dodati `--extra-index-url https://download.pytorch.org/whl/cpu` instrukciju u README.
3. Provjeriti da `app/main.py` lazy-importuje `faster_whisper` i `edge_tts` — već radi
   (linija 256, 307), ali potvrditi.
4. `lifespan` u `main.py:18` — eksplicitno preload `WhisperModel` u background task-u
   da prvi `/api/stt` ne bude lag.
5. Dokumentovati u README-u: očekivani startup time (cilj: < 15s sa CPU-only).

#### 7.3 STT fix — vraćanje na lokalni faster-whisper kao primarni — ⏸ ODGOĐENO
**Model: Sonnet 4.6 medium effort** (~3k in / 2k out)
**Status (2026-05-01):** odgođeno da se prvo benchmark-uje trenutni Groq STT vs novi
lokalni faster-whisper na realnim BCS audio uzorcima. Cilj: dokumentovati prednosti
i greške jednog i drugog prije switch-a. Vraća se nakon 7.4.

`/api/stt` u `main.py:313` trenutno prvo pokušava Groq Whisper, pa fallback na lokalni.
Groq maši — preokreni redoslijed ili ukloni Groq potpuno.

**Šta se radi:**
1. Default = lokalni `faster-whisper` (model "small", BCS dobar).
2. Groq ostaje kao **opt-in** preko env varijable `STT_PROVIDER=groq` (default: `local`).
3. Eksperimentalno isprobati `faster-whisper` "medium" model — bolji za BCS po cijenu
   ~50% sporiji. Mjeriti accuracy na 5–10 testnih audio fajlova.
4. Ako medium nije dovoljan, isprobati **Voxtral** (Mistral) ili **AssemblyAI** kao
   alternative (van scope-a Sesije 7 ako traje predugo).

#### 7.4 Prompt review + Haiku polish — ✅ ZAVRŠENO
**Model: Opus 4.7 medium effort** (~8k in / 5k out)
**Rezultat:** `BITLAB_BASE` reorganizovan na 11 jasnih pravila (8 = konkretni okidači
eskalacije, 9 = empty-search → escalate, 10 = pojačana injection odbrana, 11 = Haiku
stil "kratko, direktno"). `CHAT_FORMAT` izbacio halucinaciju "izmišljaj opis".
`VOICE_FORMAT` riješio konflikt sa `_normalize_for_tts` (brojevi ostaju brojevi).
`EMAIL_FORMAT` dobio "Bezbjednost" sekciju + delimiter logika u `main.py`. Eval
testovi #19/#20 dodati. Live testovi: 2/2 injection-a odbijena ✓

Opus radi prompt engineering kao u Sesiji 1. Cilj: smanjiti "čudna objašnjenja" Haiku-a.

**Šta se radi:**
1. Pregled `app/system_prompts.py` — tačka po tačka:
   - Da li su pravila u `BITLAB_BASE` redundantna ili u konfliktu?
   - Treba li više primjera (few-shot) za chat format?
   - Voice format — `<text>` i `<voice>` tagovi rade, ali da li XML-style limitira Haiku?
2. Dodati pravilo S3 (eskalacija pri praznom search-u — vidi 7.1).
3. Wrap email body u `<email_body>` tagove (zatvara nalaz **S2**).
4. Dopisati u `BITLAB_BASE` tačku 11: stil za Haiku — "kratko, direktno, bez fillera".
5. **Code review promptova** — provjeriti tone consistency između chat i voice (ne miješati).

#### 7.5 Workflow polish — voice → naruči → email cycle
**Model: Sonnet 4.6 medium effort** (~5k in / 4k out)

Voice mod već radi mailto link. Treba doraditi:
1. Provjeriti da `[NAZIV_PROIZVODA]` i `[CIJENA]` placeholderi se popunjavaju i u voice
   kanalu — sad samo u chat-u.
2. Email auto-reply template — u `EMAIL_FORMAT` možda dodati varijantu za "potvrda
   narudžbe primljene" kad korisnik pošalje email sa namjerom kupovine.
3. Razmotriti novi tool `prepare_order_email(product_sifra, address)` koji vraća
   strukturirani mailto URL — eliminiše Claude rad oko URL encodinga.

#### 7.6 Security backlog — V2, V3, S1, N2, N3
**Model: Sonnet 4.6 medium effort** (~6k in / 4k out)

Mehanički rad, sve specificirano u `SECURITY-REVIEW.md` (sekcija "Akcioni redoslijed"):
1. Sužavanje CORS-a + slowapi rate-limit (V2).
2. `max_length` na `TtsRequest`, file-size guard na `/api/stt` (V3).
3. Provjeri/ispravi radno vrijeme u `escalate_to_human` handler-u (S1).
4. Konstanta `app/contacts.py` (N2).
5. Pydantic validator na `anthropic_api_key` pri startu (N3).

#### 7.7 Code review (kraj Sesije 7)
**Model: Opus 4.7 high effort** (~13k in / 3k out)

Pred-produkcijski review cijelog koda — Opus pregleda sve fajlove iz `app/`, traži:
- Race condition u `lifespan` (preload modela)?
- Memory leak u `_whisper_model` global-u?
- Ko može da iscrpi memoriju? (Već smo zatvorili `/api/stt` size limit u 7.6.)
- Dead code, neiskorišteni importi.
- Konzistentnost error handling-a (sve handler-e u `tools.py` već imaju try/except —
  da li se i u `main.py` endpointi vraćaju strukturirani error?).
- Output: kratak `CODE-REVIEW.md` sa nalazima i prioritetima.

**Izlaz iz sesije 7:** Search radi za "laptop". Server starta < 15s. STT ima dobar accuracy.
Svi otvoreni nalazi iz `SECURITY-REVIEW.md` zatvoreni. Sistem je produkcijski spreman.

---

## 5. Sumarna tabela — model × effort × posao

| Sesija | Model | Effort | Glavni izlaz | Procjena tokena (in/out) |
|---|---|---|---|---|
| 0 | (ručno) | — | Ključevi, indeks | 0 |
| 1 | **Opus 4.7** | **High** | Skelet, system prompts, tool schemas | 25k / 12k |
| 2 | **Sonnet 4.6** | **High** | Agent loop, alati, RAG | 30k / 20k |
| 3 | **Sonnet 4.6** | **Medium** | Widget, voice, email, n8n JSON | 25k / 15k |
| 4 | **Sonnet 4.6** → **Opus 4.7** | **Med → High** | Evali, README, security review | 20k / 12k |
| 5 | **Sonnet 4.6** | **Low / no thinking** | Demo skript, polish | 8k / 6k |
| 6 | **Sonnet 4.6** | **Medium** | n8n lokalni hosting (ngrok out) | 10k / 6k |
| 7.1 | **Opus 4.7** | **High** | Smart product matching (laptop↔notebook) | 6k / 4k |
| 7.2 | **Sonnet 4.6** | **Medium** | CPU-only deps, brži startup | 4k / 3k |
| 7.3 | **Sonnet 4.6** | **Medium** | STT fix — lokalni faster-whisper primarni | 3k / 2k |
| 7.4 | **Opus 4.7** | **Medium** | Prompt review + Haiku polish | 8k / 5k |
| 7.5 | **Sonnet 4.6** | **Medium** | Voice → naruči → email cycle | 5k / 4k |
| 7.6 | **Sonnet 4.6** | **Medium** | Security backlog (V2, V3, S1, N2, N3) | 6k / 4k |
| 7.7 | **Opus 4.7** | **High** | Code review (kraj) | 13k / 3k |
| **Ukupno** | | | | **~163k / ~96k** |

Komotno staje u 20€ Pro budžet ako je raspoređeno preko više 5h-prozora (1 sesija po prozoru je sigurno; 2 ako su lakše).

**Token štednja u Sesiji 7:** Opus radi 3 podzadatka (7.1, 7.4, 7.7 — algoritam, prompt
engineering, code review). Sonnet radi 4 (7.2, 7.3, 7.5, 7.6 — config, STT switch,
workflow polish, security backlog). Haiku se NE koristi za ove podzadatke — sve traži
ili razmišljanje ili razumijevanje toka. Ako tokeni gore brzo, prvo izbaciti 7.5
(workflow polish) — najmanje hitan.

---

## 6. Šta NE raditi (token traps i scope creep)

- ❌ Ne pisati Supabase integraciju — lokalni `.npz` je dovoljan i jednostavniji.
- ❌ Ne klikati kroz n8n UI sa Claudeom — eksportujemo JSON, korisnik importuje.
- ❌ Ne ponovo čitati `all-products.json` u sesiji — Claude vidi samo schema.
- ❌ Ne praviti Docker/CI — lokalno pokretanje je dovoljno za demo.
- ❌ Ne praviti admin panel ili dashboard.
- ❌ Ne pisati duge docstring-e — kod govori za sebe.
- ❌ Ne praviti više embedding modela "za poređenje" — jedan multilingual mini-LM je dovoljan.

---

## 7. Copilot CLI (GPT-5) kao backup

**Kada koristiti:**

- Ako Claude prozor presahne usred sesije, a treba završiti **mehanički** kod (HTML/CSS, boilerplate funkcije, konverzija JSON formata).
- Za **drugi par očiju** na sistem prompt-u (postoji li bias u BCS jeziku?).
- Za **bulk generaciju** test pitanja u `evals/test_questions.json` ako Claude troši previše.

**Kako:**
```bash
gh copilot suggest "napravi HTML widget launcher dugme sa orange-#FB923C bojom..."
# ili
gh copilot explain "..."
```

**Kada NE:** Ne koristiti za agent loop, tool dispatch, system prompt. Tu Claude (Opus posebno) ima prednost zbog tool-use know-howa i trening podataka.

---

## 8. Pitch (90s) — kako se prezentuje

Live demo redoslijed:

1. **Chat (20s):** Otvorim widget na test stranici. Pitam: *"Imate li Patriot SSD 240GB?"* → AI vraća proizvod sa cijenom i linkom iz pravih 5.287 stavki kataloga.
2. **FAQ (15s):** *"Kolika je dostava u Mostar?"* → AI odgovara iz `faq.md` (kurirani sadržaj sa sajta).
3. **Voice (15s):** Voice mod, glasovno pitanje, native BCS odgovor (Lara).
4. **Email (20s):** Pošaljem testni email *"Treba mi ponuda za 5 SSD-ova za firmu"* — za 30s stiže profesionalan auto-reply, ali sa eskalacijom na `prodaja@bitlab.rs` jer treba JIB.
5. **Evali (10s):** Pokrenem `python evals/run.py` → tabela 17/18 prolazi.
6. **Cijena (10s):** "Claude API ~$15–25/mjesečno za realan saobraćaj. Sve ostalo (embeddings, n8n free tier, hosting) je $0."

**Glavna poruka:** *"Ostali su isporučili demo. Mi smo isporučili sistem koji se sutra pušta u produkciju — nad pravim katalogom od 5.287 proizvoda, na tri kanala, sa mjerljivom kvalitetom."*

---

## 9. Zaključane odluke (✓ potvrđeno)

| Stavka | Odluka |
|---|---|
| Voice glas | **Lara** — mlađa, prodajna, BitLab cilja širu publiku |
| Web framework | **FastAPI** + `uvicorn` |
| Razvojno okruženje | **Lokalno**, Python `.venv`, `uvicorn app.main:app --reload` |
| Email automatizacija | **n8n cloud (free tier)** sa IMAP node-om |
| Tunneling za n8n → lokalni server | **`ngrok` free** (n8n cloud mora dosegnuti `localhost`) |
| Email trigger | **IMAP** (n8n native node, bez Gmail OAuth) |
| Retrieval | **Hibrid: BM25 + vektor** (score fusion 0.4/0.6) — BCS skraćenice/SKU brojevi inače loše embed-uju |
| Reranker | **Ne za MVP** — top-5 hibrid je dovoljno; dodajemo tek ako evali padnu ispod 15/18 |

### Šta je hibrid retrieval (kratko podsjećanje)

Dvije pretrage paralelno, kombinovani skorovi:

- **Vektor (cosine nad embeddingsima):** razumije značenje (*"brzi disk"* → SSD), ali fula skraćenice (*"DDR4"*, *"1TB"*) i SKU brojeve (*"PBU120GS25SSDR"*).
- **BM25 (keyword):** lovi tačne riječi i brendove (*"Patriot 240GB"*), ali ne razumije parafraze (*"garderoba"* ≠ *"ormar"*).
- **Fusion:** `final_score = 0.6 × vektor + 0.4 × bm25` (oba normalizovana 0–1), top-5 ide u kontekst Claude-u.

Kritično za BitLab jer je IT/elektronika — pun SKU brojeva, brendova, skraćenica (RAM, SSD, GPU, DDR4, NVMe).

---

**Sve potvrđeno → krećemo Sesiju 1 sa Opus 4.7 / high effort.**

---

## 10. Redoslijed izvršavanja od MVP-a do produkcije

> **Datum dogovora:** 2026-05-01
>
> Sesije 0–5 su završene (MVP isporučen). Sesije 6 i 7 dodate nakon Sesije 4 security
> review-a + bugova prijavljenih iz testiranja. Ovaj redoslijed je dogovoren sa korisnikom
> i prati se do kraja produkcijskog ciklusa.

### Faza A — ✅ MVP (završeno)
| # | Sesija | Status |
|---|---|---|
| 1 | Sesija 0 — Priprema | ✅ |
| 2 | Sesija 1 — Arhitektura, skelet, system prompt | ✅ |
| 3 | Sesija 2 — Agent loop, alati, RAG | ✅ |
| 4 | Sesija 3 — Kanali (widget + voice + email + n8n) | ✅ |
| 5 | Sesija 4 — Evali + polish + security review (vidi `SECURITY-REVIEW.md`) | ✅ |
| 6 | Sesija 5 — Demo prep i pitch | ✅ |

### Faza B — 🔥 Hot path: kritični demo bugovi (sad)

Razlog redoslijeda: 7.2 prvi jer brzi startup ubrzava sve naredne iteracije. Onda 7.1
zato što search koji ne nalazi laptopove razbija demo. Onda 7.3 jer voice mod sa lošim
STT-om je neupotrebljiv.

| # | Podzadatak | Model | Tokeni (in/out) | Status |
|---|---|---|---|---|
| 7 | **7.2 CPU-only deps** — brži startup (cilj < 15s) | Sonnet 4.6 medium | 4k / 3k | ✅ Startup pao sa 60s na **2.7s** (lazy import + bg preload + pin ST<4) |
| 8 | **7.1 Smart product matching** — laptop ↔ notebook | Opus 4.7 high | 6k / 4k | ✅ `category_terms.json` + 3× prefix u indeksu + search-time boost; "laptop", "notebook", "matična ploča", "powerbank", "tv" sve rade. 19/19 testova ✓ |
| 9 | **7.3 STT fix** — lokalni faster-whisper primarni | Sonnet 4.6 medium | 3k / 2k | ⏸ Odgođeno za benchmark Groq vs lokalni |

**Izlaz iz Faze B:** demo-ready sistem. Ako tokeni presahnu, ovo je sigurna tačka.

### Faza C — ⏳ Security cleanup

| # | Podzadatak | Model | Tokeni (in/out) | Status |
|---|---|---|---|---|
| 10 | **Sesija 6** — Migracija n8n na lokalni hosting (zatvara V1) | Sonnet 4.6 medium | ~3k / 2k* | ✅ n8n/email-autoreply.json → host.docker.internal; ngrok uklonjen iz README + HOSTING; server guide u README Sekcija 10 |

\* Stvarna potrošnja je niska jer je pola posla ručno (Docker, n8n UI). Claude troši
tokene samo na update `n8n/email-autoreply.json` URL-a i `HOSTING.md` uputstva.

### Faza D — 🧹 Polish + zatvaranje security backlog-a

| # | Podzadatak | Model | Tokeni (in/out) | Status |
|---|---|---|---|---|
| 11 | **7.6 Security backlog** — V2, V3, S1, N2, N3 (mehanički) | Sonnet 4.6 medium | 6k / 4k | ☐ |
| 12 | **7.4 Prompt review + Haiku polish** | Opus 4.7 medium | 8k / 5k | ✅ 11 pravila + injection delimiter; 2/2 injection testa odbijena |
| 13 | **7.5 Voice → naruči → email cycle** *(opciono)* | Sonnet 4.6 medium | 5k / 4k | ☐ |
| 14 | **7.7 Code review** — pred-produkcijski sweep | Opus 4.7 high | 13k / 3k | ☐ |

**Izlaz iz Faze D:** sistem produkcijski spreman. Otvoreni nalazi iz `SECURITY-REVIEW.md`
zatvoreni. Code review čist.

### Pravila za toku izvršavanja

1. **Token budžet — ako tanji od 30k preostalih:** preskoči 7.5 (najmanje hitan).
2. **Ako 7.1 (smart matching) traje predugo:** Opus se vraća i radi minimalnu varijantu
   (proširiti hardkodiranu listu sinonima u `tools.py`); puno rješenje (category dictionary
   iz baze) odlazi u Fazu D ili kasnije.
3. **Sesija 6 može se odraditi i bez Claude-a:** Docker pull + n8n import + manuelni
   URL update. Claude se zove samo za commit izmjene `n8n/email-autoreply.json`.
4. **Posle svake faze:** quick smoke test (`python scripts/smoke_test.py` + ručni demo flow)
   prije nego se ide u sljedeću fazu.
5. **7.3 STT switch zahtijeva benchmark (2026-05-01 odluka):** prije nego se Groq Whisper
   skine sa primarnog mjesta, snimaju se 5–10 BCS audio uzoraka, transkribuju oba
   providera, dokumentuje accuracy/error tabela u `docs/stt-benchmark.md`. Tek tada
   odluka koji ide u default.

---

**Trenutni korak: 7.4 — Prompt review + Haiku polish.**
