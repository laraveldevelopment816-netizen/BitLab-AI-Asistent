# BitLab AI Asistent — Handoff za Claude Code

> **Cilj:** Implementirati novi hi-fi dizajn (chat widget + voice modal) preko **postojećeg** `widget.js` i `voice.html` koda. **Nikakva izmjena backend logike** (VAD, fetch, state machine, recording) nije potrebna — samo CSS + minorne HTML strukturne izmjene.

---

## 1. Šta predati Claude Code agentu

Kreiraj folder `handoff/` u repo-u i unutra stavi:

```
handoff/
├── README.md                            ← ovaj dokument
├── design/
│   ├── BitLab Asistent — Hi-Fi.html     ← interaktivni hi-fi (svi state-ovi)
│   └── screenshots/                     ← export-uj 7 screenshot-a iz canvas-a
│       ├── 01-launcher.png
│       ├── 02-welcome.png
│       ├── 03-conversation.png
│       ├── 04-typing.png
│       ├── 05-voice-idle.png
│       ├── 06-voice-listening.png
│       └── 07-voice-speaking.png
├── tokens/
│   └── widget.css                       ← finalni dizajn tokeni + svi style-ovi
└── current/
    ├── widget.js                        ← TRENUTNI fajl (referenca)
    └── voice.html                       ← TRENUTNI fajl (referenca)
```

Sve već postoji u ovom projektu — samo iskopiraj `hifi/widget.css`, `hifi/components.jsx` (kao referencu HTML strukture) i screenshot-uj canvas.

---

## 2. Prompt za Claude Code

```
Implementiraj novi UI za BitLab AI Asistent prema fajlovima u handoff/.

KONTEKST
- Postojeći embeddable widget je u public/widget.js (chat + voice u jednom fajlu).
- Standalone voice page je u public/voice.html.
- Backend (FastAPI na /api/chat, /api/stt, /api/tts) NE treba mijenjati.
- Sva JS logika (VAD, recording, state machine, history, markdown render, interrupt detection) MORA ostati funkcionalno identična. Samo izgled se mijenja.

ZADACI

1. Zamijeni CSS blok u widget.js novim iz handoff/tokens/widget.css.
   - Sve postojeće DOM ID-eve (#bl-launcher, #bl-window, #bl-messages,
     #bl-input, #bl-send, #bl-voice-btn, #bl-voice-overlay, itd) MORAJU
     ostati identični — JS event handleri ih koriste.
   - Klase u CSS-u koristi nove, čiste imena (.bl-msg, .bl-msg--bot, .bl-orb,
     .bl-orb__core, .bl-orb__ring) prema widget.css.

2. Ažuriraj insertAdjacentHTML markup u widget.js da odgovara hi-fi
   strukturi iz screenshot-a. Promjene:
   - Header: dodaj avatar (44x44, orange, rounded 14px) sa bot ikonom +
     online dot u donjem desnom uglu avatara. Title "BitLab Asistent",
     subtitle sa pulse-dot + "Online · Odgovara odmah". Dva icon button-a
     desno (minimize, close) — svaki 32x32, rounded 10px, bg
     rgba(white,0.08).
   - Ispod headera: red sa 3 chip-a (Sigurno, AI, "5.278 proizvoda")
     tonalna chip pozadine.
   - Welcome ekran (prikazuje se kad je #bl-messages prazan): 64x64 avatar
     orb sa spark ikonom, naslov "Pozdrav.", subtitle, i 3 vertikalna
     suggest button-a (laptop / gaming / dostava) — svaki sa orange
     ikonom u rounded square-u, naslov + opis, strelica desno.
   - Quick replies: pojavljuju se SAMO kad ima poruka (sakri u welcome
     state). Label "Brza pitanja" caps tracking, chips imaju ikone.
   - Input: wrap u rounded-pill kontejner sa attach (paperclip) ikonom
     unutra, voice button (rounded, 42x42, neutral), send button
     (rounded, 42x42, orange gradient).
   - Footer: "Pokreće BitLab AI · Šifrovano · webshop.bitlab.rs"

3. Voice modal — restruktuiraj #bl-voice-panel:
   - Header (navy gradient): mic ikona u rounded square (orange tinted),
     title + state line sa colored dot, close button.
   - Stage: VEĆI orb (160x160 wrapper, 96x96 core), 3 koncentrična ringa
     koji pulsiraju (animation-delay 0s/1s/2s), inner core sa mic ikonom.
     - Boja core-a po state-u:
       - idle:      orange gradient (#fb6d3b → #ea5c2a)
       - listening: green gradient (#16a34a → #15803d)
       - speaking:  orange gradient (zadrži orange — promijeni samo wave)
     - Ring border-color prati state.
   - Velika linija ispod orb-a sa transcript-om — 18px, weight 500,
     center-balanced.
   - Ispod toga: waveform (15-20 vertikalnih stick-ova koji pulsiraju)
     tokom listening/speaking; hint pill tokom idle.
   - Ispod: "vidljive" zadnje 2 poruke (user + bot) u istim bubble
     stilovima kao chat.
   - Footer: 2 button-a — Pauziraj (neutral) i Zaustavi (danger tinted).
   - Ukloni: stari level-bar strip ispod headera, stari mali orb u
     headeru, stari big orb u centru (zamijeni novim 160px orb-om sa
     ringovima).

4. Mobile (< 440px): widget je full-width sa 8px margine, voice modal je
   full-screen.

5. Markdown render-er, product card formatting iz bot odgovora — zadrži.
   Samo dodaj klase za novi izgled product card-a (.bl-prod, .bl-prod__img,
   .bl-prod__name, .bl-prod__price, .bl-prod__avail).

ŠTA NE DIRATI
- Nikakva izmjena u VAD logici (SPEECH_THRESHOLD, ONSET_GAP_MS, itd).
- Nikakva izmjena u fetch pozivima ili payload-ima.
- history[] array i njegova upotreba ostaje 1:1.
- TTS fallback chain (server → window.speechSynthesis) ostaje.
- Sigurno-context check za mikrofon ostaje sa istom porukom.

VERIFIKACIJA
- Otvori widget.html lokalno, klikni launcher → vidiš welcome screen.
- Pošalji testno pitanje → quick replies se sakriju, pojavi se
  conversation sa product card-ovima ako backend vrati slike.
- Voice button → otvori voice modal sa orange orb idle state.
- Govori → orb postane zelen, ring puls promijeni boju, waveform aktivan.
- Završi rečenicu → orb postane orange, transcript line pokazuje šta AI
  govori.
- Stop button zatvara modal.
- Provjeri na mobilnom širinom (Chrome DevTools → 375px).

DELIVERABLES
1. Modifikovani public/widget.js (jedan fajl, čisto kao prije).
2. Modifikovani public/voice.html (standalone — koristi iste tokene
   ali samostalan, bez chat dijela).
3. Kratak CHANGELOG.md u root: šta je dodano, šta je uklonjeno.
4. Screenshot prije/poslije svakog state-a u handoff/after/.
```

---

## 3. Acceptance kriteriji (za review)

| # | Kriterij | Provjera |
|---|---|---|
| 1 | Launcher ima orange gradient + ring puls + badge "1" | Pogledaj na webshop-u, idle state |
| 2 | Header je navy gradient sa orange decorative wedge u uglu | DevTools — vidi `::after` |
| 3 | Welcome screen ima 3 suggest button-a sa orange ikonama | Otvori prvi put, prazan #bl-messages |
| 4 | Bot bubble: bijeli, hairline border, soft shadow, 16px radius | Inspect bubble |
| 5 | User bubble: orange gradient, donji-desni ugao 6px | Inspect |
| 6 | Product card ima orange-tinted thumb, brand caps, tabular price | Pitaj "imate li SSD" |
| 7 | Typing indicator: 3 orange dot-a koji bounce (ne sivi) | Tokom čekanja odgovora |
| 8 | Quick replies sakriveni dok je welcome, pojavljuju se posle prve poruke | State change |
| 9 | Input wrap: rounded-pill, focus state ima orange ring + bg shift | Klik u input |
| 10 | Voice orb: 160px wrapper sa 3 ringa, 96px core, mic ikona | Otvori voice |
| 11 | Voice listening: orb je zelen, ring border-color zelena | Govori |
| 12 | Waveform: 15+ stick-ova sa staggered animation-delay | Listening/speaking |
| 13 | Voice ima 2 button-a: Pauziraj (neutral) + Zaustavi (danger) | Footer modala |
| 14 | Mobile: widget full-width sa 8px margine, voice full-screen | DevTools 375px |
| 15 | Sve postojeće funkcije (VAD, STT, TTS, interrupt, history) rade | E2E test |

---

## 4. Tehnički savjeti za Claude Code

**Strategija refaktora.** Ne pokušavaj sve odjednom. Idi ovim redom:

1. **Replace CSS string** u `widget.js` — to je najveći blok, ali najbezbjedniji. Test posle toga: stari HTML + novi CSS → vidjećeš da ID-evi i dalje rade ali izgled je polurazbijen (jer markup je stari).

2. **Replace HTML markup string** (`document.body.insertAdjacentHTML('beforeend', ...)`). Drži iste ID-eve, dodaj nove klase. Test: cijeli widget izgleda kao novi.

3. **Welcome screen**: u `addMsg` funkciji ili u launcher click handler-u, ako je `#bl-messages` prazan, render-uj welcome blok umjesto prve `addMsg('Pozdrav!...')` poruke. Klik na bilo koji suggest button → pozovi `sendMessage(...)`.

4. **Voice modal**: zadrži `setVoiceState()` mapping ali izmijeni klasu na orb-u i tekst na velikoj liniji. Dodaj waveform render — može biti čisto CSS (15 span-ova, animation-delay = index*0.08s).

5. **Standalone voice.html**: replikuj iste tokene ali bez chat dijela. To je čisti port — uzmi voice modal markup iz novog widget.js i obmotaj ga page-level layout-om.

**Potencijalne zamke:**

- `mic-btn` u voice.html ima conditional className-ove (`state-listening`, `state-recording`, itd). U novom dizajnu ti se mapiraju u `bl-orb--listening`, `bl-orb--speaking` itd. Pazi da ne razbiješ CSS animacije koje se trigguju klasom.
- Markdown render-er u oba fajla treba istu funkciju — extract u helper ili kopiraj.
- Product card iz bot odgovora dolazi kao `<img>` + tekst u markdown-u. Možda ćeš trebati post-processor koji detect-uje "image + price na lageru" pattern i wrap-uje u `.bl-prod` strukturu — ili (jednostavnije) ostaviti server da emit-uje već formatiran HTML i samo dodati `.bl-prod` klase.

---

## 5. Open pitanja za product owner-a (prije starta)

Pitaj prije coding-a:

1. **Avatar u headeru** — koristi bot SVG ikonu (kao sad u dizajnu) ili stvarni BitLab logo grafiku?
2. **Welcome suggest button-i** — fiksni (Laptopi / Gaming / Dostava) ili izvuče se iz QUICK_REPLIES array-a?
3. **Online status** — uvijek "Online · Odgovara odmah" ili stvarni health check na `/api/chat`?
4. **Footer copy** — "webshop.bitlab.rs" tačno? Da li dodati i broj telefona?
5. **Mobile breakpoint** — 440px je granica za full-width. Da li ostaje?
6. **Voice "Pauziraj" button** — trenutni kod nema pause, samo stop. Da li dodati pravu pauzu (cancelAnimationFrame VAD ali zadrži stream) ili izbaciti dugme?

---

## 6. Šta agent NE smije promijeniti

🚫 Backend rute / payload-ove
🚫 VAD konstante
🚫 TTS fallback chain
🚫 history[] strukturu
🚫 Cooldown timing posle TTS-a (TTS_COOLDOWN_MS = 750ms — postoji s razlogom: reverb)
🚫 Secure-context check error message + chrome:// flag instrukcije

✅ CSS, HTML markup, klase
✅ Dodavanje suggest screena
✅ Restrukturu voice modala
✅ Premještanje stop dugmeta

---

**Procjena vremena:** 4–6h za senior-a koji zna projekat, 1 radni dan za novog. Najveći rizik: product card markup mismatch — testiraj odmah s par realnih backend odgovora.
