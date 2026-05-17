# Voice mode — migration plan + debugging

Komplementaran [`features/voice-mode.md`](features/voice-mode.md) koji opisuje
UX flow + state machine. Ovaj fajl pokriva ElevenLabs migration kandidat i
debugging recepte.

## Trenutno stanje

Voice mode je live u widget-u. STT: Groq Whisper. TTS: Azure Speech Services
(primarno) sa edge-tts fallback-om. ElevenLabs migracija je razmatrana na
LIVE testu 2026-05-08 i preskočena — ostala je kandidat za kasnije.

---

## Plan A — ElevenLabs migracija (kandidat)

Bolji UX za BCS od Azure-a, ali skuplji. Da bi se aktivirao:

### 1. Nabavi ključ + voice ID

- https://elevenlabs.io → Sign up / Login → API key u Profile
- Voice library: izaberi **Multilingual** voice (radi BCS). Predlog: probaj
  2–3 ženska glasa, snimi 10s sample sa BCS rečenicom, biraj. Bitno: model
  **eleven_multilingual_v2**, ne v1 ni Turbo (Turbo ne podržava HR/SR dobro).

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

Ostavi Azure i edge-tts blokove kakvi su — oni su fallback ako ElevenLabs
padne.

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
~150 znakova → **~$0.045 po odgovoru**. Free tier 10K karaktera/mjesec →
potroši za prvih ~70 odgovora. Provjeri tier prije aktivacije.

---

## Debugging — otkrivanje hidden voice button-a (legacy)

Tokom LIVE testa 2026-05-08 voice button je bio privremeno sakriven
(`style="display:none"` na `bl-voice-btn` u `public/widget.js`). Hide je
kasnije uklonjen, ali ako se ikad ponovo doda za debug:

```bash
# u widget.js, ukloni `style="display:none"` na voice button-u
sed -i 's/aria-label="Voice mode" style="display:none">/aria-label="Voice mode">/' public/widget.js
```

---

## Vraćanje voice-a (ako je button sakriven) — tri koraka

Ako se voice button u nekom budućem trenutku ponovo sakrije
(`style="display:none"`), evo procedure za vraćanje sa ElevenLabs-om:

1. Brana commit-uje ElevenLabs patch iz koraka 3-4 (Plan A).
2. Revertuje voice button hide u `public/widget.js` (ukloni
   `style="display:none"` na `bl-voice-btn`).
3. Push na main, deploy na prod, reload widget na webshop-u (tvrdi refresh).
