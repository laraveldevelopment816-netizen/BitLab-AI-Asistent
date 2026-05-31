# Voice mode

> Glasovni razgovor sa AI asistentom — STT (govor → tekst), agent loop, TTS (tekst → govor) + vizualna paleta proizvoda.

## UX flow

```
1. Korisnik klikne mikrofon u widget-u → openVoiceMode()
   → fullscreen orb, centriran, 160px (idle stanje)

2. getUserMedia() → mikrofon stream → VAD (voice activity detection)
   → state: LISTENING (orb zelena)

3. Korisnik počinje govoriti
   → state: RECORDING (orb zelena + wave animacija)
   → snimi do silence detection (1.5s tišine = kraj)

4. WebM blob → POST /api/stt
   → state: PROCESSING (orb plava + thinking sound "tu-nu-nu")

5. STT vrati tekst → POST /api/chat (channel='voice')
   → još uvijek PROCESSING

6. Reply stigne sa <text> i <voice> blokom:
   → fullscreen orb se animirano skuplja u kompaktan header (~25%)
   → transcript fade-in iz dna (~75%) sa product cards
   → POST /api/tts sa voice tekstom → audio.play()
   → state: SPEAKING (orb plava + wave)

7. TTS završi → state: LISTENING (čeka sledeći upit)
   → korisnik može da govori ili klikne stop
```

## State machine

```
IDLE          → klik mic → LISTENING
LISTENING     → speech detected (200ms RMS) → RECORDING
RECORDING     → silence (1500ms) → PROCESSING
PROCESSING    → STT + chat + TTS gotov → SPEAKING
SPEAKING      → audio.ended → LISTENING (auto loop)
SPEAKING      → korisnik prekida (interrupt VAD) → LISTENING
*             → klik stop → close + reset
```

VAD parametri u `widget.js`:
- `SPEECH_THRESHOLD = 0.035` — RMS prag (viši = manje osjetljivo na šum)
- `SPEECH_ONSET_MS = 200` — sustained signal pred markiranje "speech"
- `SILENCE_MS = 1500` — koliko tišine = "korisnik završio"
- `INTERRUPT_THRESHOLD = 0.18` — viši prag (samo jak korisnički glas, ne reverb)
- `INTERRUPT_HOLD_MS = 350` — mora govoriti 350ms za prekid (filter AI glasa iz zvučnika)

## Backend XML format

Voice channel system prompt (`VOICE_FORMAT`) traži dva bloka:

```
<text>
[Bogata vizuelna paleta — markdown, product cards, slike, linkovi]
</text>

<voice>
[Kratki govorni sažetak — 2-3 rečenice, BEZ markdowna, BEZ URL-ova,
 cijene kao brojevi sa jedinicom: "389 KM" — backend pretvara u govor]
</voice>
```

`agent.py` `_parse_voice_xml()` izvlači oba dijela:
- `reply` (UI text dio) → ide u widget chat balon
- `reply_voice` (TTS dio) → ide u `/api/tts`

Defensive: ako Claude pošalje samo `<voice>` bez `<text>`, parser uzima sve van `<voice>` bloka kao reply_text. Ako Claude propusti tagove uopšte, fallback — prve 2 rečenice plain teksta za voice.

## TTS — Azure → edge-tts fallback chain

`POST /api/tts` u `app/main.py`:

1. **Azure Speech Services** (ako je `AZURE_SPEECH_KEY` postavljen) — primarni, najbolji kvalitet za bs/hr/sr (Vesna, Gabrijela, Sophie...)
2. **edge-tts** (uvijek dostupan, bez ključa) — koristi iste Azure neural glasove neoficijalno

Default voice: `hr-HR-GabrijelaNeural`. Override kroz `TTS_VOICE` env var ili `voice_id` u request body.

### Cijene normalizacije za TTS

`_normalize_for_tts()` pretvara markdown + cifre u oblik za TTS:
- `1.936 KM` → "hiljadu devetsto trideset šest maraka"
- `389,99 KM` → "trista osamdeset devet maraka"
- `16GB` → "šesnaest gigabajta"
- `3.5GHz` → "tri gigaherca" (decimalni dio se ne čita za freq)
- Markdown (`**bold**`, `[link](url)`, slike) — strip
- Emoji — strip (TTS čita kao naziv karaktera)

**Bug fix Sesija 8:** prije, `1.936` se kastovalo u `float(1.936) → int(1) = "jedna marka"`. Sad heuristika hvata BCS format gdje je tačka separator hiljada.

## STT — Groq → Azure → faster-whisper fallback chain

`POST /api/stt` u `app/main.py`:

1. **Groq Whisper-large-v3** (ako je `GROQ_API_KEY` postavljen) — najbolji za bs/hr/sr, free tier 7.200s/dan
2. **Azure Speech-to-Text** (ako je `AZURE_SPEECH_KEY`) — fallback
3. **Lokalni faster-whisper** (model `small`, ~150MB) — offline fallback

Domain prompt utisnut u Whisper poziv da bolje hvata IT termine + lokalna imena (BitLab, Banja Luka, brend imena).

### Hallucination filter

Whisper na tihoj snimci ponekad transcribuje "Hvala", "thank you", "...". `_clean_stt()` ih briše:
```python
_HALLUCINATIONS = {"hvala", "hvala vam", "thank you", ".", "..", "...", " ", ...}
```

## Voice widget UI (Sesija 8 redesign)

| State panel | Layout |
|---|---|
| **Idle / fullscreen** (prije prvog rezultata) | Orb 160px centriran preko cijelog widget-a |
| **Sa rezultatima** (poslije addVoiceMsg prvi put) | Header 25% (orb 64px + state pill + wave + tline), body 75% (transcript sa product cards, flex:1) |

Tranzicija je CSS animacija (0.35s cubic-bezier) na orb width/height + stage padding.

`vp-fullscreen` modifier klasa kontroliše state. `setVoiceFullscreen(false)` triggeruje skupljanje kad addVoiceMsg pozove prvi put.

## Thinking sound

Web Audio API procedural — pattern "tu-nu-nu":
- 3 pulsa: 110 Hz → 165 Hz → 247 Hz (svaki 75ms, 140ms gap)
- Sub-oktava komponenta (55/82/123 Hz) sa 0.05 gain za bass tijelo
- Master peak gain 0.07 (vrlo tiho)
- 12ms attack, 25ms release (sprečava clicks)
- 700ms pauza između grupa, ponavlja
- Stop = setInterval cleared, gain envelope na 0

Aktivira se na `VS.PROCESSING`, deaktivira na bilo koji drugi state.

## Persistencija razgovora

`history = []` se dijeli između chat i voice mode-a. Pređi sa chat-a u voice — AI ima puni kontekst.

Reset transkripta na svaki `openVoiceMode()` (clean slate). Chat balončići u widget-u ostaju.

## Implementacija

| Element | Lokacija |
|---|---|
| Voice modal markup + CSS | `public/widget.js` (inline) |
| State machine + VAD | `widget.js` `setVoiceState()`, `startVad()` |
| STT request | `widget.js` `POST /api/stt` (multipart audio) |
| TTS request | `widget.js` `POST /api/tts` (JSON {text, voice_id}) |
| Voice XML parsing | `app/agent.py` `_parse_voice_xml()` |
| TTS normalizacija | `app/main.py` `_normalize_for_tts()` |
| STT pipeline | `app/main.py` `api_stt()` |
| Thinking sound | `widget.js` `startThinkingSound()`, `_playPulse()` |

## Tipični problemi

- **Mikrofon ne radi:** Web Speech API zahtijeva HTTPS ili `localhost`. Chrome `chrome://flags/#unsafely-treat-insecure-origin-as-secure` za testing.
- **Firefox:** ne podržava Web Speech (radi samo Chrome/Edge).
- **Prvi /api/chat traje 30-50s:** sentence-transformers preload na cold start. Sledeći ide normalno.
- **TTS čita `<voice>` tagove:** Sesija 8 fix — `_strip_voice_tags()` u backendu + frontend defensive layer.
