# Code review — Sesija 7 / tačka 7.7 (pred-produkcijski sweep)

**Reviewer:** Claude Opus 4.7 (high effort)
**Datum:** 2026-05-02
**Scope:** `app/` (10 fajlova, 1.547 linija), `pyproject.toml`, `tests/test_tools.py`.

Cilj: race conditions, memory leaks, error-handling konzistentnost, dead code,
potencijalni DoS / blokiranje event loop-a. Pretpostavlja se da su V2/V3/S1/S2/S3/N2/N3
iz `SECURITY-REVIEW.md` već zatvoreni (verifikovano u 7.6).

---

## Sumarna tabela nalaza

| ID | Težina | Naslov | Fajl |
|----|--------|--------|------|
| C1 | 🟠 P1 | Sync Anthropic SDK blokira async event loop | `app/agent.py:73`, `app/main.py:149,177` |
| C2 | 🟠 P1 | TOCTOU race u 4 lazy-singleton inicijalizacije | `rag.py:128`, `main.py:326`, `agent.py:41`, `tools.py:147` |
| C3 | 🟡 P1 | Whisper model nije preload-ovan u lifespan (7.2 leftover) | `app/main.py:21` |
| C4 | 🟡 P1 | `api_chat`/`api_email`/`api_tts` bez endpoint-level try/except | `app/main.py:140,160,272` |
| C5 | 🟢 P2 | `get_event_loop()` deprecated u async kontekstu | `app/main.py:342,398` |
| C6 | 🟢 P2 | Tihi `except Exception: pass` na Groq/ElevenLabs fallback-u | `app/main.py:308,389` |
| C7 | 🟢 P2 | `_HALLUCINATIONS` set se rekreira na svaki STT poziv | `app/main.py:360` |
| C8 | 🟢 P2 | `settings = Settings()` na import time + obavezan validator | `app/config.py:23,83` |
| C9 | ⚪ Nice | `_NUM_BCS` / `_n2w` / `_normalize_for_tts` ~80 linija u `main.py` | `app/main.py:188-269` |
| C10 | ⚪ Nice | `np.load(...)` bez `with` — `NpzFile` objekat curi u memoriji | `app/rag.py:91` |
| C11 | ⚪ Nice | Inkonzistentan URL field — `search` rekonstruira, `check_availability` koristi raw | `app/tools.py:181,225-230` |

**Vodeća poruka:** sistem je **funkcionalno produkcijski spreman**, ali pod
istovremenim opterećenjem (>5 paralelnih korisnika u chatu) C1 + C2 mogu
proizvesti latency spike-ove i dvostruki load `SentenceTransformer`-a (~150 MB
+ 50s na WSL2). **C1 je najvažniji zatvoriti.**

---

## P1 nalazi

### C1. Sync Anthropic SDK blokira FastAPI event loop

**Fajl:** `app/agent.py:73`, pozivan iz `app/main.py:149,177`.

`run_agent()` zove `client.messages.create(...)` (sync), unutar `async def api_chat`
i `async def api_email`. Svaki Claude poziv (typično 1–3s) **blokira cijeli
event loop** — drugi requestovi (uključujući `/healthz`, TTS, STT) čekaju.

Sa 30 req/min rate-limita po IP-u i više IP-ova istovremeno (widget na
webshop-u + voice + n8n email pipeline), uvicorn mora obraditi u serijama što
duplicira p95 latency i pravi vidljive zastoje na widget-u.

**Fix (10 min):**
```python
# app/main.py:149
result = await asyncio.to_thread(run_agent, messages, channel=req.channel)
```
Isto za `api_email:177`. Trošak: 1 dodatni thread po requestu (Python ima
default thread pool — OK pod realnim opterećenjem).

**Alternative (čisto, ali veći touchpoint):** prebaciti na
`anthropic.AsyncAnthropic` i `async def run_agent`. Ostalo (tools, dispatch)
ostaje sync — pozivi alata su milisekunde, ne blokiraju.

---

### C2. TOCTOU race u lazy-singleton inicijalizaciji

**Fajlovi:**
- `app/rag.py:128` — `ProductIndex.preload_model`
- `app/main.py:326` — `_get_whisper`
- `app/agent.py:41` — `_get_client`
- `app/tools.py:147` — `_get_faq`

Sve četiri funkcije imaju isti obrazac:
```python
if _x is None:
    _x = SkupiKonstruktor(...)
return _x
```
bez lock-a. Konkretan race scenarij u `rag.py`:

1. `lifespan` startuje `asyncio.to_thread(idx.preload_model)` u backgroundu.
2. Prvi `/api/chat` stigne za <50s (npr. 5s posle uvicorn starta).
3. `run_agent` → `handle_search_products` → `idx.search(query)` → `_embed(query)` →
   `if self._model is None: self.preload_model()` u **drugom thread-u**.
4. Oba thread-a **istovremeno** rade `SentenceTransformer(embed_model)`. Nije
   crash, ali se modeli učitavaju duplo: ~150 MB transient + ~50s import.

Slično za `_get_whisper` — preload nikad ne počinje (vidi C3), pa će prvi
istovremeni STT zahtjev pokrenuti **dvije** instance WhisperModel-a (~300 MB).

**Fix (15 min):** dodati `threading.Lock` u svaki helper:
```python
import threading
_index_lock = threading.Lock()

def get_index() -> ProductIndex:
    global _index
    if _index is None:
        with _index_lock:
            if _index is None:
                _index = ProductIndex()
    return _index
```
Double-checked locking — fast path bez lock-a, slow path (prvi poziv) zaštićen.

Isto za `_client`, `_whisper_model`, `_faq_sections`. Za `ProductIndex._model`
dodati `self._model_lock = threading.Lock()` u `__init__` i zaštititi
`preload_model`.

---

### C3. Whisper model nije preload-ovan u lifespan (7.2 leftover)

**Fajl:** `app/main.py:21-34`.

Sesija 7.2 je tražila eksplicitan preload Whisper modela u background task-u
(plan tačka 4: *"`lifespan` u `main.py:18` — eksplicitno preload `WhisperModel`
u background task-u da prvi `/api/stt` ne bude lag."*). U trenutnom kodu se
preload-uje **samo** sentence-transformers (`idx.preload_model`).

Posljedica: prvi `/api/stt` request još uvijek čeka 5–10s na initialization
WhisperModel-a (CPU int8, "small" ~150 MB).

**Fix (5 min):**
```python
# u lifespan, nakon postojećeg preload-a:
asyncio.create_task(asyncio.to_thread(_get_whisper))
```
Background, ne blokira startup. Sa C2 fix-om (lock), sigurno za istovremeni
prvi request.

---

### C4. Endpointi bez try/except → traceback u 500 odgovoru

**Fajlovi:** `api_chat:140`, `api_email:160`, `api_tts:272`. (`api_stt` već
ima parcijalni guard za Groq path.)

`run_agent` može baciti `anthropic.APIError` (rate limit, timeout, 5xx),
`anthropic.AuthenticationError`, ili network `httpx.ConnectError`. Trenutno se
sve to vraća kao FastAPI default 500 sa traceback-om u logu (i potencijalno
u response body-ju u dev mode-u).

`api_tts` slično — `edge_tts.Communicate.stream()` može padati na rare DNS
greške ili Microsoft 5xx.

**Fix (15 min):** centralni `@app.exception_handler(Exception)` koji vraća
`{"error": "service_unavailable", "detail": "..."}` 503, plus per-endpoint
hvatanje očekivanih `anthropic.APIStatusError`:
```python
try:
    result = await asyncio.to_thread(run_agent, messages, channel=req.channel)
except anthropic.APIStatusError as e:
    raise HTTPException(status_code=502, detail=f"Anthropic upstream: {e.status_code}")
except anthropic.APIConnectionError:
    raise HTTPException(status_code=503, detail="Anthropic nedostupan, pokušajte uskoro.")
```
Dodati simetrično u `api_email`, `api_tts`.

---

## P2 nalazi

### C5. `asyncio.get_event_loop()` deprecated u async kontekstu

**Fajl:** `app/main.py:342,398`.

`from asyncio import get_event_loop` + `loop = get_event_loop()` u `async def
api_stt`. Python 3.12 baca `DeprecationWarning`; 3.14 može ukloniti.

**Fix:** prebaciti na `asyncio.to_thread`:
```python
model = await asyncio.to_thread(_get_whisper)
segments, info = await asyncio.to_thread(
    model.transcribe, tmp_path,
    language="hr", beam_size=5,
    no_speech_threshold=0.6, log_prob_threshold=-1.0,
)
```
Čistije, bez `loop` varijable.

---

### C6. Tihi `except Exception: pass` na cloud fallback-u

**Fajlovi:** `app/main.py:308` (ElevenLabs), `app/main.py:389` (Groq).

Ako ElevenLabs vrati 401 (istek ključa) ili Groq 429 (rate limit), pad na
fallback je tih — nema log-a, nema metrike. Tek kad se javi user da je glas
"drugačiji", debug počinje od nule.

**Fix:** dodati osnovan `logging`:
```python
import logging
log = logging.getLogger(__name__)
...
except Exception as e:
    log.warning("ElevenLabs nedostupan, fallback na edge-tts: %s", e)
```
Nije nužno strukturisani logger — `logging.basicConfig(level=INFO)` u
uvicorn-u dovoljan za nalaženje obrazaca.

---

### C7. `_HALLUCINATIONS` set se rekreira na svaki STT poziv

**Fajl:** `app/main.py:360-365`.

Set sa 14 stringova alocira se na svaki `/api/stt`. Ne mjerljiv perf hit, ali
je idiomatski loše — definiše ga se na module scope-u kao `frozenset(...)`.

---

### C8. Import-time validator → tests/CI bez `.env` ne mogu da urade ni `import app`

**Fajlovi:** `app/config.py:23,83`.

`Settings()` se instancira na import time. `_require_api_key` baca
`ValueError` ako je `ANTHROPIC_API_KEY` prazan. To znači:
- `pytest tests/` u čistom CI okruženju **bez** `.env` puca pri importu
  `app.tools` (koji importuje `app.config`).
- Trenutni testovi rade samo zato što razvojni `.env` ima ključ; CI bi morao
  imati real ili dummy ključ.

**Opcije:**
1. Mekša validacija: dozvoli prazan ključ, ali ga **prvi `run_agent` poziv**
   detektuje i baca jasnu grešku. Tests koji ne zovu Anthropic prolaze čisto.
2. Ili: dodati `conftest.py` sa `monkeypatch.setenv("ANTHROPIC_API_KEY",
   "sk-test")` fixture-om i dokumentovati u README.

Preporuka: **Opcija 1** — startup validator je u principu dobar UX, ali ne
treba ići preko ValueError u import time-u; bolja je provjera na prvi
`_get_client()` poziv ili u `lifespan`. Trenutno jedini razlog što
`docs/`/`schema-only` request u CI-ju radi je sreća.

---

## Nice-to-have

### C9. Razdvojiti TTS pomoćne funkcije iz `main.py`

`_NUM_BCS` (10 linija), `_n2w` (16 linija), `_normalize_for_tts` (54 linije)
zauzimaju ~80 linija u sredini `main.py`. Routing fajl je 413 linija a polovinu
čini brojevna konverzija. Predlog: `app/tts_utils.py` — `main.py` se smanji na
~330, lakša navigacija.

Nije urgent, čisto code hygiene.

### C10. `np.load` bez `with` — `NpzFile` objekat curi

**Fajl:** `app/rag.py:91`. `data = np.load(...)` ne zatvara fajl handler.
Pošto je jednom-pri-startu, OK, ali idiomatski:
```python
with np.load(settings.products_index) as data:
    self.embeddings = data["embeddings"].copy()  # mora copy ako se data zatvara
    self.ids = data["ids"].copy()
```

### C11. URL field inkonzistentan između `search` i `check_availability`

**Fajl:** `app/tools.py:181`, `app/rag.py:225-230`.

`search()` u `rag.py` rekonstruira URL kao
`https://webshop.bitlab.rs/{slug}.html`. `handle_check_availability` u
`tools.py:181` vraća `meta.get('url', 'N/A')` — sirov field iz `meta.json`,
koji je u formatu `proizvod/{urlhash}` bez `.html`. Korisnik koji klikne URL
iz `check_availability` rezultata dobija 404.

**Fix:** ekstraktovati istu URL-rekonstrukciju u `_meta_to_url(meta)` helper i
zvati iz oba mjesta.

---

## ✅ Što je dobro

- Pydantic validacija na svim request body-jima (max_length, pattern, list
  size). Eksplicitno i centralizovano.
- Tool dispatcher u `tools.py:212` ima generički try/except — nijedan tool
  poziv ne ruši agent loop.
- `agent.py` parsira voice XML sa fallback-om na "prve dvije rečenice" ako
  Claude ne vrati `<voice>` tag — robusno.
- `_trim_email_preamble` garantuje čist email format bez Claude meta-komentara.
- `run_agent` kapira broj iteracija na `settings.max_tool_iterations=5` —
  nema infinite tool-call loop-a.
- Whisper STT halucinacije filtrirane (`_clean_stt`); empty string return
  bolji nego "hvala vam" lažnog transkripta.
- Lazy import-i `faster_whisper`, `edge_tts`, `sentence_transformers` — bez
  njih bi startup bio neupotrebljiv (potvrđeno u 7.2).
- Single source of truth za kontakte (`app/contacts.py`) — N2 zatvoren čisto.
- Tests pokrivaju FAQ + tools dispatcher + product search edge cases (no-result,
  price filter, top_k). Indeks-zavisni testovi se preskaču gracefully.

---

## Akcioni redoslijed (preporuka)

| # | Akcija | ID | Težina | Procjena |
|---|---|---|---|---|
| 1 | `asyncio.to_thread(run_agent, ...)` u `api_chat` + `api_email` | C1 | 🟠 P1 | 10 min |
| 2 | Threading lock-ovi u 4 lazy-singleton helpera | C2 | 🟠 P1 | 15 min |
| 3 | Whisper preload u lifespan | C3 | 🟡 P1 | 5 min |
| 4 | Try/except wrap u `api_chat`/`api_email`/`api_tts` + struktur. error response | C4 | 🟡 P1 | 15 min |
| 5 | `asyncio.to_thread` u `api_stt` umjesto `get_event_loop` | C5 | 🟢 P2 | 5 min |
| 6 | Logging na cloud fallback-u (Groq + ElevenLabs) | C6 | 🟢 P2 | 5 min |
| 7 | `_HALLUCINATIONS` u module scope kao `frozenset` | C7 | 🟢 P2 | 2 min |
| 8 | Mekša API key validacija (lazy umjesto import-time) | C8 | 🟢 P2 | 10 min |

**Ukupno P1: ~45 min.** Sa P2: **~75 min.** Ostalo (C9–C11) ostaviti za
buduće sesije ili "u prolazu" PR-ove.

---

## Memory / DoS sweep — verifikacija

- `/api/stt` upload: 25 MB Content-Length guard + 25 MB data guard ✓
- `/api/chat` history: 20 poruka × 4000 chars = 80 KB max ✓
- `/api/email` body: 8000 chars max ✓
- `/api/tts` text: 2000 chars max ✓
- `slowapi` rate-limit per-IP (in-memory dict) — bounded by uvicorn process
  lifetime, ne curi van restart-a ✓
- WhisperModel singleton (~150 MB) — drži se za cijeli process lifetime,
  očekivano ✓ (nije leak)
- `_index.embeddings` (~5.287 × 384 × 4B = ~8 MB) — drži se, očekivano ✓

**Zaključak:** memory profile je predvidljiv i bounded. Glavni rizik nije
exhaustion već **CPU starvation pod blokiranim event loop-om** (C1).

---

**Status MVP-a:** produkcijski spreman za demo i kontrolisani roll-out.
Sa P1 fix-evima (~45 min) spreman i za otvoreni saobraćaj sa webshop.bitlab.rs.
