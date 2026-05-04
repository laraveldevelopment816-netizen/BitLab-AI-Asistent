# ⚠️ DEPRECATED — ovaj plan je napušten

> **Ovaj fajl opisuje prvobitnu Node.js / Express verziju plana iz aprila 2026** koja nikad nije implementirana. Stvarni MVP je Python/FastAPI.
>
> **Aktuelni dokumenti:**
> - **`BITLAB-MVP-PLAN.md`** — važeći MVP plan (Python/FastAPI, sesije 0–7)
> - **`PRODUCTION-PREP-PLAN.md`** — plan za produkciju (Sesija 8)
>
> Sve niže je istorijski referent — **ne pratiti**.

---

# BitLab AI Asistent — Plan za prolazak u drugi krug

> **Cilj:** Izdvojiti se od ~10 učesnika i ući u uži izbor za angažman.
> **Resurs:** Jedna kompletna Claude Code sesija na 20€ Pro pretplati.
> **Datum:** 2026-04-29.

---

## 1. Šta će ostali (skoro sigurno) napraviti

Svi imaju isti `dan4` paket (widget demo, voice demo, n8n vodič, RAG vodič). Realno očekujem od većine:

- Kopiran `demo_widget.html`, prebojen u BitLab boje, hardkodovan kratak system prompt sa par činjenica.
- Možda 2–3 učesnika probaju Supabase RAG, ali samo sa 5–10 ručno napisanih dokumenata (kao u vodiču za GMP).
- Skoro niko neće povezati **widget + voice + n8n email auto-reply** u jedno rješenje.
- Niko neće stvarno indeksirati svih **5.287 proizvoda** iz `data/all-products.json`.
- API ključ će biti u HTML-u (nesigurno) — kao u demou.
- Bez deployovanog URL-a, bez evaluacija, bez ROI brojki.

**Pobjeđujemo ako isporučimo cjelovit, produkcijski-uredan sistem koji rješava sva tri kanala (chat, voice, email) nad pravom bazom proizvoda i FAQ-om.**

---

## 2. Naš diferencijator — "trifecta + production polish"

Šest stvari koje, zajedno, niko drugi neće imati:

1. **Tri kanala, jedna baza znanja:**
   - Web widget (chat) — embeddable `<script>` blok
   - Voice agent (ElevenLabs BCS glas)
   - Email auto-reply preko n8n
   Sva tri zovu **isti backend** sa **istim alatima** (RAG + FAQ + escalation).

2. **Pravi RAG nad 5.287 proizvoda + FAQ sa sajta.** Ostali će imati 5 ručno upisanih dokumenata. Mi imamo cijeli katalog.

3. **Tool-using agent (ne čisti chatbot).** Alati: `search_products`, `check_availability`, `get_faq`, `escalate_to_human`. Ovo prati Dan 4 "agent" definiciju — DJELUJE, ne samo odgovara.

4. **Sigurna arhitektura:** Backend proxy čuva API ključeve (ne u HTML-u). Ostali će preskočiti ovo.

5. **Mjerljiv kvalitet:** Mali eval set (15–20 realnih pitanja) sa očekivanim ponašanjem. Pokazujemo "70%+ pitanja AI rješava sam" sa brojkama.

6. **Deploy + demo paket:** Live URL (Vercel/Render free tier), 90-sekundni Loom snimak, README sa ROI računicom (Claude Haiku troškovi po 1k pitanja).

---

## 3. Arhitektura

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
                            ▲     ▲      ▲
                  ┌─────────┘     │      └────────────┐
                  │               │                   │
          ┌───────────────┐ ┌────────────┐  ┌──────────────────┐
          │ Web widget    │ │ Voice HTML │  │ n8n Email flow   │
          │ (na sajtu)    │ │ (BCS TTS)  │  │ Gmail → API →    │
          │               │ │            │  │ Reply automatski │
          └───────────────┘ └────────────┘  └──────────────────┘

Knowledge base:
  - products.index.json  (5287 proizvoda + embeddings, lokalni vector store)
  - faq.json             (FAQ sa webshop.bitlab.rs, ručno kurirano)
```

**Zašto lokalni JSON vector store, ne Supabase:** Štedimo sesijske tokene (nema klik-po-klik setup-a) i zavisnosti. 5287 × 1536 floatova ≈ 32 MB — sasvim u redu za in-memory cosine search na malom serveru. Ako bude vremena na kraju, dodajemo Supabase kao bonus.

**Zašto Node.js backend:** Jednofajlni `server.js`, isti runtime kao widget, jednostavan deploy na Render/Vercel free.

**Zašto Claude Haiku 4.5 (`claude-haiku-4-5-20251001`):** Brzina + niska cijena, kako kursni materijal preporučuje. Sonnet samo za email auto-reply (duži, formalniji odgovori).

---

## 4. Strategija štednje tokena (kritično — imamo jednu sesiju)

Pravilo: **Claude Code piše KOD, ne istražuje podatke i ne klika kroz UI.**

### Pripremni rad PRIJE Claude Code sesije (radi se ručno / lokalnim skriptama):

- [ ] **Ja ručno** otvorim `webshop.bitlab.rs`, kopiram FAQ/Dostava/Plaćanje/Garancija sekcije u `data/faq.md` (~10 minuta, 0 tokena).
- [ ] **Ja ručno** napravim API ključeve: Anthropic, OpenAI (za embeddings), ElevenLabs, n8n nalog. Stavim u `.env.example`.
- [ ] **Ja ručno** registrujem deploy target (Render free tier — jedan klik GitHub login).
- [ ] **Lokalna python skripta** (bez Claude Code-a) generiše embeddings za 5287 proizvoda → `products.index.json`. Ovo je ~$0.10 OpenAI troška, ali 0 sesijskih tokena.

### Ponašanje u sesiji:

- **Ne čitati `all-products.json` direktno u Claude.** 5287 redova × 40 polja bi pojeo kontekst. Skripta ga konzumira, Claude vidi samo schemu.
- **Plan-first režim:** prvih 5 minuta sesije — `/plan`, fiksiramo svaku datoteku i sadržaj, pa onda u jednom potezu izvršimo.
- **Batch tool calls.** Kad god je moguće, paralelne edit/write pozive u jednoj poruci.
- **Ne tjerati Claude da debug-uje runtime greške koje mogu sam vidjeti u browseru.** Ja pokrećem, lijepim samo trace.
- **Eval i n8n config su tekstualni JSON-ovi** — Claude ih napiše jednom, ja importujem klikom u n8n UI.
- **Subagent samo za konkretan, izolovan posao** (npr. "napiši `embed_products.py` skriptu") — ne za istraživanje.

### Procjena tokena (gruba):
| Faza | Procjena |
|---|---|
| Plan + skeleton (server.js, package.json, .env) | ~15k input / 5k output |
| Tool definicije + agent loop | ~10k / 8k |
| Widget HTML + brending | ~10k / 8k |
| Voice HTML adaptacija | ~6k / 4k |
| n8n workflow JSON | ~5k / 3k |
| Eval skripta + 15 test pitanja | ~6k / 4k |
| README + deploy instrukcije | ~4k / 3k |
| Debug rezerva | ~20k / 10k |
| **Ukupno** | **~76k / 45k** — komotno u jednoj sesiji |

---

## 5. Plan rada u sesiji (linearni redoslijed)

Sve je dizajnirano da se može prekinuti i nastaviti. Ako tokeni počnu da nestaju, **prioriteti su 1→7**, ostalo je bonus.

### Korak 1 — Skelet projekta (must-have)
```
/server.js                 Express, /api/chat endpoint, env loader
/lib/agent.js              Agent loop (Claude tool use)
/lib/tools.js              Tool definicije + handleri
/lib/rag.js                Cosine similarity nad products.index.json
/lib/faq.js                Učitava data/faq.md, jednostavan keyword + LLM rerank
/public/widget.html        Embeddable widget
/public/voice.html         Voice mode (Web Speech STT + ElevenLabs TTS)
/scripts/embed_products.py Lokalna skripta (ne sesija) — generiše products.index.json
/data/faq.md               Ručno kurirano (FAQ sa sajta)
/n8n/email-autoreply.json  Workflow export, importuje se klikom
/evals/test-questions.json 15–20 pitanja sa očekivanim alatom/odgovorom
/evals/run.js              Pokreće sva pitanja, ispisuje pass/fail
.env.example
README.md
package.json
```

### Korak 2 — Agent + alati (must-have)
- `search_products(query, top_k=5)` — RAG nad indexom, vraća ime/cijenu/dostupnost/link
- `get_faq(topic)` — vraća relevantnu FAQ sekciju
- `check_availability(product_id)` — čita `kolicina`, `ProductAvailability` polja
- `escalate_to_human(reason)` — vraća Viber/email kontakt sa kratkim sažetkom upita

System prompt je **jedan fajl** (`lib/system-prompt.md`), isti za sva tri kanala — samo se mijenja channel kontekst (chat/voice/email).

### Korak 3 — Web widget (must-have)
Krenuti od `docs/dan4/demo_widget.html`, ali:
- API ključ NIJE u HTML-u — fetch ide na naš `/api/chat`
- BitLab boje (analizirati sa webshop.bitlab.rs — orange/dark)
- "Pitaj AI" launcher u donjem desnom uglu
- Tipping indicator, Markdown render za odgovore (linkovi do proizvoda)
- Mobile responsive
- `<script src="https://nasa-domena/widget.js">` jedan-blok integracija

### Korak 4 — Voice mode (visoka vrijednost)
- Bazirati na `demo_voice_v2.html`, ali poziva naš `/api/chat` i naš `/api/tts`
- Native BCS glas iz ElevenLabs (npr. **Lara** ili **Jusuf**)
- Otključava use case "vozač pita za proizvod hands-free"

### Korak 5 — n8n email auto-reply (najveći diferencijator)
Workflow:
```
Gmail trigger (novi email)
  → IF (subject contains "upit"|"ponuda"|"cijena"|"dostava"|"garancija")
  → HTTP POST → naš /api/email
  → Gmail Reply
  → Slack/Telegram notif (opcionalno)
```
- `/api/email` koristi **isti agent**, ali sa email-system promptom (formalnije, potpis BitLab)
- Ako agent pozove `escalate_to_human` → ne šalje auto-reply, samo notif vlasniku

### Korak 6 — Evali (pokazuje inženjerski pristup)
`evals/test-questions.json`:
```json
[
  {"q":"Imate li SSD 1TB?","expect_tool":"search_products"},
  {"q":"Dostavljate li u Mostar?","expect_tool":"get_faq"},
  {"q":"Trebam ponudu za firmu, JIB...","expect_tool":"escalate_to_human"},
  ...
]
```
Skripta pokrene sve, ispiše tabelu pass/fail. **U pitch-u:** "Sistem prolazi 18/20 realnih pitanja."

### Korak 7 — Deploy + README + pitch (must-have za prezentaciju)
- Push na GitHub
- Deploy backend na Render free tier (Node)
- Deploy widget kao statički fajl (Vercel ili isti Render)
- README: arhitektura (slika gore), kako pokrenuti, troškovi, ROI
- **Pitch sekcija u README-u:**
  - "Sva tri kanala u jednom danu, 24/7"
  - "5.287 proizvoda u realnom RAG-u"
  - "$10–30 mjesečno za Claude API"
  - "70%+ pitanja riješi AI sam (eval rezultati: 18/20)"

### Bonus (ako ostane vremena/tokena)
- Supabase RAG kao alternativa lokalnom JSON-u (pokazuje skalabilnost)
- Admin dashboard sa logovima razgovora
- Streamovanje odgovora (SSE) za bolji UX
- Loom snimak (90s) ugrađen u README

---

## 6. Šta NE raditi (token traps)

- ❌ Ne pokušavati admin panel sa autentikacijom — preveliki scope.
- ❌ Ne pisati testove za svaku funkciju — samo `evals/run.js`.
- ❌ Ne preferirati apstrakcije/factory pattern. Linearno, pragmatično.
- ❌ Ne dirati `all-products.json` u sesiji — sve ide kroz `products.index.json`.
- ❌ Ne pokušavati kloniranje glasa vlasnika BitLab-a (ElevenLabs $5 plan, traje, rizik).
- ❌ Ne raditi Telegram/WhatsApp bot — n8n email je dovoljan diferencijator.
- ❌ Ne pisati duge komentare/dokumentaciju u kodu — samo gdje je razlog netrivijalan.

---

## 7. Pred-sesijska checklist (radim večeras / sutra ujutro)

- [ ] Anthropic API ključ (već imam za sesiju, treba i za deploy)
- [ ] OpenAI API ključ (samo za embeddings, ~$0.10 jednokratno)
- [ ] ElevenLabs nalog + Voice ID (npr. Lara — Croatian)
- [ ] n8n cloud nalog (free tier)
- [ ] Render.com nalog povezan sa GitHub-om
- [ ] FAQ tekst kopiran sa webshop.bitlab.rs → `data/faq.md`
- [ ] BitLab brand boje (HEX) zabeležene
- [ ] `scripts/embed_products.py` pokrenuta lokalno → `products.index.json` postoji
- [ ] Prazan GitHub repo `bitlab-ai-asistent` napravljen

Kad je sve ovo gotovo, sesija je ČISTO pisanje koda i deploy.

---

## 8. Kako se ovo prezentuje žiriju

90 sekundi pitch + live demo:

1. Otvorim **webshop.bitlab.rs** sa našim widgetom — pitam "Imate li SSD 1TB do 200KM?" → AI vraća listu proizvoda sa cijenama i linkovima.
2. Kliknem voice mode — pitam glasom "Kolika je dostava do Mostara?" → AI odgovara native BCS glasom.
3. Pošaljem email "Treba mi ponuda za 5 SSD-ova za firmu" sa testnog naloga → za 30s stiže profesionalni reply potpisan BitLab-om, sa eskalacijom na prodaja@bitlab.rs jer treba JIB.
4. Pokažem `evals/run.js` — 18/20 pitanja prolazi.
5. README slide: troškovi $10–30/mj, ROI 5h sedmično.

**Glavna poruka:** "Ostali su napravili demo. Mi smo napravili sistem koji se sutra može pustiti u produkciju."

---

## 9. Otvorena pitanja (potrebne odluke prije sesije)

- **Hosting:** Render free tier (preporuka — Node-friendly) ili Vercel (serverless, malo komplikovaniji za Express)?
- **Voice glas:** Lara (mlađa, prodajna) ili Jusuf (ozbiljna B2B nota)? Predlažem Laru jer BitLab cilja široku publiku.
- **Embedding provider:** OpenAI `text-embedding-3-small` ($0.02/1M, dokazano) ili Voyage AI (EU, malo skuplji)? Predlažem OpenAI.
- **Backend jezik:** Node.js (preporuka — isti runtime kao widget) ili Python (kao demo_agent.py)? Predlažem Node.
- **n8n:** stvarni Gmail trigger (treba Google OAuth, traje) ili IMAP (jednostavniji)? Predlažem IMAP za demo, Gmail u README kao "produkcijska verzija".

Daj zeleno svjetlo na ovih 5 i krećemo u sesiju.
