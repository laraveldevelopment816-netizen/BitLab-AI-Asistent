# LIVE test BitLab AI Asistent — 2026-05-08, 11:00–17:00

**Odluka: idemo bez voice-a danas.** Voice mode je privremeno sakriven u
widgetu (`bl-voice-btn` ima `style="display:none"` u `public/widget.js`).
Backend i dalje servira `/api/tts` i `/api/stt` u slučaju da Branislav
završi ElevenLabs implementaciju do 11h — tada vrati widget.

Ivan prati uživo s telefona. Branislav na standby-u za backend restart
ako se pojavi greška.

---

## Šta se mijenja danas u 11:00

1. **Chat widget LIVE** na `webshop.bitlab.rs` (script tag dolje)
2. **Voice dugme sakriveno** — korisnici vide samo chat ikonu
3. **Backend live** na `https://aiasistent.bitlab.rs` sa novim AI search
   poboljšanjima (89 kategorija + 90 brendova vs 13/0 prije)

---

## Embed snippet za webshop (proslijedi Brani do 11:00)

Brana ovo dodaje pred `</body>` na webshop.bitlab.rs:

```html
<script>window.BITLAB_API='https://aiasistent.bitlab.rs';</script>
<script src="https://aiasistent.bitlab.rs/public/widget.js" defer></script>
```

To je sve. Widget se pojavi kao orange chat bubble u donjem desnom uglu.

Ako Brana traži test-prvo varijantu (staging):

```html
<script>window.BITLAB_API='https://staging.aiasistent.bitlab.rs';</script>
<script src="https://staging.aiasistent.bitlab.rs/public/widget.js" defer></script>
```

---

## Šta pratimo 11:00–17:00

Otvori dashboard u tabu na telefonu/laptopu:
**`https://aiasistent.bitlab.rs/admin/`** (Bearer ključ je u `shared/.env`
servera, podsjetnik: env var `DASHBOARD_API_KEY`).

| Tab | Šta gledamo | Akcija ako vidiš |
|---|---|---|
| **Sessions** | Broj ulazaka, broj poruka po sesiji, koliko ide do `escalate_to_human` | >5 escalate u 30 min = problem, otvori History |
| **History** | Filter na `channel=chat` — pročitaj 5–10 random sesija svaka 30 min | Halucinacija o cijenama / nepostojećim proizvodima → zovi Branislava |
| **Tool calls** | `search_products` poziv treba imati `category_id` i (često) `brand_id` popunjen | Ako su prazni za očigledne upite ("samsung tv") → AI ne klasifikuje, javi nam |
| **Errors** | Crveni badge na vrhu | Otvori Sessions → klikni sesiju → vidi trace |

Na telefonu dashboard je responsive. Brzi pristup: bookmark
`https://aiasistent.bitlab.rs/admin/sessions`.

---

## Plan za backend restart (ako zabugue)

SSH na prod server (Brana ima ključ; Ivan može sa svog laptopa):

```bash
ssh ai@ai.bitlab.rs
sudo systemctl restart aiasistent-prod
sudo systemctl status aiasistent-prod   # provjera da je active (running)
curl -sf https://aiasistent.bitlab.rs/healthz   # treba 200 OK
```

Ako je restart pomogao, vrati se na dashboard. Ako i dalje 502/500:

```bash
sudo journalctl -u aiasistent-prod -n 100 --no-pager
```

Pošalji zadnjih 30 linija loga na Viber Branislavu.

---

## Kako vratiti voice (ako Brana stigne ElevenLabs)

Tri koraka:

1. Brana commit-uje ElevenLabs patch u `app/main.py` + `app/config.py` +
   `.env` (vidi sekciju "Plan A" dolje za detalje).
2. Reverteruje voice button hide u `public/widget.js` (vrati ga bez
   `style="display:none"`).
3. Push na main, deploy na prod, reload widget na webshopu (tvrdi refresh).

---

## Plan A — ElevenLabs implementacija (ako stigne)

### 1. Nabavi ključ + voice ID

- https://elevenlabs.io → Sign up / Login → API key u Profile
- Voice library: izaberi **Multilingual** voice (radi BCS). Predlog: probaj
  2–3 ženska glasa, snimi 10s sample sa BCS rečenicom, biraj. Bitno: model
  **eleven_multilingual_v2**, ne v1 ni Turbo (Turbo ne podržava HR/SR
  dobro)

### 2. Dodaj u `shared/.env` na serveru

```
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxx
ELEVENLABS_VOICE_ID=xxxxxxxxxxxx
ELEVENLABS_MODEL=eleven_multilingual_v2
```

### 3. Patch `app/config.py` — dodaj 4 nova polja

Pod sekcijom `# ── TTS glas ...`:

```python
    # ── ElevenLabs (primarni TTS — bolji UX za BCS od Azure-a) ──
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
```

### 4. Patch `app/main.py` — `/api/tts` endpoint

Otvori `app/main.py`, nađi `async def api_tts(...)` (oko linije 334).
**Iznad** bloka `# ── Azure Speech Services (primarno kad je ključ
postavljen) ──` ubaci:

```python
    # ── ElevenLabs (primarni — najbolji UX za BCS) ──────────────
    if settings.elevenlabs_api_key and settings.elevenlabs_voice_id:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}",
                    headers={
                        "xi-api-key": settings.elevenlabs_api_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                    json={
                        "text": tts_text,
                        "model_id": settings.elevenlabs_model,
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "style": 0.0,
                            "use_speaker_boost": True,
                        },
                    },
                )
            if resp.status_code == 200 and resp.content:
                return Response(content=resp.content, media_type="audio/mpeg")
            print(f"[TTS] ElevenLabs failed: {resp.status_code} {resp.text[:200]!r}")
        except Exception as e:
            print(f"[TTS] ElevenLabs exception: {e!r}")
    # ── (fall through na Azure → edge-tts kao sigurnosna mreža) ──
```

Ostavi Azure i edge-tts blokove kakvi su — oni su fallback ako
ElevenLabs padne.

### 5. Test prije restart-a

```bash
# Sintaksa OK
python -c "from app.main import app; print('imports ok')"

# Restart
sudo systemctl restart aiasistent-prod

# Smoke test TTS-a
curl -X POST https://aiasistent.bitlab.rs/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Dobar dan, ovo je BitLab AI Asistent. Kako mogu da vam pomognem?"}' \
  --output /tmp/test.mp3
mpv /tmp/test.mp3   # ili scp na laptop pa play
```

### 6. Cost watchout

ElevenLabs Creator plan: **~$0.30/1000 znakova**. Prosječan voice odgovor
~150 znakova → **~$0.045 po odgovoru**. Za 6h testa sa 30–80 voice sesija:
$1–10. Free tier 10K karaktera/mjesec → potroši za prvih ~70 odgovora.
**Postavi tier prije 11h** ili nestaje sredinom testa.

---

## Plan B — Trenutno stanje (voice je sakriven)

Widget je već updated. Backend ne treba ništa raditi. Voice button neće
biti prikazan u UI-ju.

Da otkriješ voice button privremeno (debugging na lokalu):

```bash
# u widget.js linija 952, ukloni `style="display:none"`
sed -i 's/aria-label="Voice mode" style="display:none">/aria-label="Voice mode">/' public/widget.js
```

---

## Eskalacijski put danas

| Šta | Akcija |
|---|---|
| Backend down (502/503) | SSH → `systemctl restart aiasistent-prod` |
| TTS šalje 503 (ako ipak pustimo voice) | Provjeri da fallback chain radi (Azure ili edge-tts) |
| STT halucinira ("hvala", "...") | Već imamo guard `_HALLUCINATIONS` u `/api/stt` |
| Halucinacije proizvoda u chat-u | Pošalji sifru/sesija ID na Viber, gledamo da li je nova pretraga riješila |
| Korisnik traži B2B / JIB | Trigger-uje `escalate_to_human` automatski — Brana dobija email |

Hitno → Viber.

---

## Šta je novo backend-side

`feature/ai-search-brand-category-improvements` branch je merged u staging
+ main 2026-05-08. Donosi:

- **89 kategorija** sa 500 BCS termina (vs 13/50)
- **Brand awareness** — 90 brendova, AI klasifikuje brand_id pored
  category_id
- **Bidirectional prefix match** — "monitor" sad hvata cat 224 (term je
  "monitori" plural)
- **Head-noun fallback** — "samsung tv" → cat 163, "gaming miš" → cat 277

Detalji: [`docs/features/ai-search-improvements.md`](docs/features/ai-search-improvements.md).

Tokom testa pratimo da AI uistinu koristi `brand_id` u tool call-ovima
(History → Tool calls tab). Ako ne — vraćamo se na to sutra.
