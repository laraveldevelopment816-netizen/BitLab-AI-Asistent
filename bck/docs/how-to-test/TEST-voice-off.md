# Lokalno testiranje — Voice modul off (chat-only deploy)

Dev se diže direktno preko uvicorn-a u Python venv-u — u repou nema Docker
compose-a niti container image-a. URL je `http://localhost:8000`.

## Pokretanje

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Prvi `/api/chat` poziv čeka da RAG embedding model završi background grijanje
(~50s na WSL2 `/mnt/c`). `/healthz` odgovara odmah.

Ako je port 8000 zauzet (na WSL2 setupu često Docker Desktop iz Windows-a
proxy-uje portove 8000-8090), dodaj `--port 7777` ili neki drugi slobodan
port i zamijeni URL u svim curl pozivima ispod.

## Test plan — Voice modul off (STATUS kartica `vmoff`)

Sve četiri provjere moraju proći prije nego što kartica ide u Done. DoD izvor:
[`docs/plans/dod-chat-only.md`](docs/plans/dod-chat-only.md) sekcija 1.

### 1. Server se diže bez voice grijanja

Pokreni uvicorn i posmatraj startup log. Ne smije biti pomena
`faster_whisper`, `edge_tts` ili Whisper inicijalizacije. RAG embedding
preload (`sentence-transformers`) ostaje — to je chat dependency.

### 2. Chat tok radi (golden path)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Imate li laptop do 2000 KM?"}'
```

Očekivano: HTTP 200, JSON sa `reply` poljem. Ovo je glavna garancija da
gašenje voice modula nije slomilo chat.

### 3. Voice rute su mrtve (sve tri)

```bash
curl -i http://localhost:8000/api/voice/status
curl -i -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" -d '{"text":"test"}'
curl -i -X POST http://localhost:8000/api/stt -F "audio=@/dev/null"
```

Očekivano: sve tri vraćaju HTTP 404 (FastAPI default za neregistrovanu
rutu). Ne 500, ne 200.

### 4. Health endpoint zelen

```bash
curl -s http://localhost:8000/healthz | jq
```

Očekivano: `status: "ok"`, RAG indeks polja `true`.

### 5. Frontend ne dodiruje voice rute

Otvori `http://localhost:8000/` u browser-u (root vraća `public/widget.html`),
hard-reload (Ctrl+Shift+R) da preskoči cache, otvori DevTools → Network tab,
i klikni chat bubble.

Sve tri provjere moraju proći:

- **Mikrofon button hidden** — u input row-u ne smije biti voice ikona.
- **Network tab čist od voice ruta** — filtriraj po "voice", "tts", "stt".
  Ne smije postojati nijedan zahtjev. To dokazuje da frontend zaista ne
  zove backend voice handlere.
- **Console čista** — nema `[BitLab] Voice mode disabled` ili
  `Voice status check failed` warning-a (oni su nuspojava pre-flight
  fetch-a koji sad ne radi).

Mehanizam: `public/widget.js:23` ima `const VOICE_ENABLED = false`. Sa
`false`, pre-flight IIFE (`widget.js:1919-1934`) se ne izvršava, voice
button ostaje sa default `style="display:none"` iz markup-a
(`widget.js:961`). Voice handler funkcije (`openVoiceMode`, STT/TTS
pozivi) ostaju u kodu — nikad se ne pozivaju jer click event ne dolazi
sa skrivenog button-a.

## Reaktivacija voice modula (kasnija faza)

Tri toggle-a, sva tri u commit-u:

1. `app/main.py` — ukloni `#` ispred dekoratora `@app.post("/api/tts")`,
   `@app.post("/api/stt")`, `@app.get("/api/voice/status")` (i njihovih
   `@limiter.limit(...)` pratitelja).
2. `public/widget.js:28` — promijeni `VOICE_ENABLED = false` u `true`.
3. Provjeri da `GROQ_API_KEY` ostaje postavljen u `.env`/server config —
   bez njega `voice/status` vraća `voice_available: false` i widget krije
   button (postojeća logika).
