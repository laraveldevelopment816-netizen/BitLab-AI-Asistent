# Chat widget

> Embeddable chat na `webshop.bitlab.rs` — jedan `<script>` tag.

## Integracija

```html
<!-- pred </body> tag na webshop sajtu -->
<script src="https://aiasistent.bitlab.rs/public/widget.js"></script>
```

Widget kreira floating button u donjem desnom uglu, klik → otvori modal sa welcome screen-om i quick reply chip-ovima.

## Flow

1. Korisnik klikne welcome chip ili kuca u input
2. `widget.js` POST na `/api/chat` sa `{message, history, channel:'chat'}`
3. Dok čeka odgovor — typing indicator + thinking sound (Web Audio "tu-nu-nu")
4. Reply stigne → `renderMarkdown()` parsira:
   - **Defensive layeri:** strip `<voice>` tagova, multi-line product collapse, `---` strip
   - Product cards iz line format-a
5. Bot poruka skroluje na **vrh** (ne dno) — prvi rezultat se vidi prvi
6. Suggestions / quick replies za follow-up

## Product card format

Backend se trudi da uvijek vrati single-line:
```
- ![](image_url) **Ime** — 929 KM — Na lageru — [Pogledaj](url)
```

Renderer (`PROD_RE` u `widget.js`) hvata to i pretvara u kartice:

```
┌─────────────────────────────────────────┐
│ [slika]  ASUS E1504FA 15,6"  [→]        │
│          929 KM    ✓ Na lageru          │
└─────────────────────────────────────────┘
```

Ako Claude razbije format na više redova (slika u jednom, ime u drugom, cijena u trećem), `collapseMultiLineProducts()` pokušava sklopiti single-line ekvivalent. Ima conservative guard:
- Bez slike ne sklapa (sprečava false positive — npr. "**Pažnja**: 500 KM")
- Bold ime mora biti ≥8 znakova (sprečava da kratki bold tekst kvalifikuje)

## Defensive layers

`renderMarkdown()` u `widget.js` radi sledeće prepass-e:

1. **Voice tag strip** — uklanja `<voice>...</voice>` blok ako procuri (TTS-only sadržaj ne smije u UI)
2. **Multi-line product collapse** — sklopi razbijene kartice u single-line
3. **`---` separator strip** — Sonnet voli da ubaci horizontal rule između proizvoda; uklanjamo
4. **`(N kom)` strip** — Claude i dalje dodaje `(1 kom)`, briše se preventivno
5. **Standard markdown** — `**bold**`, `[link](url)`, `![](img)`, line breaks

## State

```js
const history = [];  // [{role, content}, ...] — prosljeđuje se na svaki request
let chatOpened = false;
```

Sve drugo je per-request (typing indicator se uklanja kad reply stigne).

## Voice handoff

Mikrofon dugme u widget-u → `openVoiceMode()` → otvori voice overlay (vidi [`voice-mode.md`](./voice-mode.md)).

`history` se dijeli između chat i voice — ako pređeš sa chat-a u voice, AI ima puni kontekst razgovora.

## Reset / clear

Trenutno: refresh stranice. Welcome screen se vraća, history se briše.

## Sound

Thinking sound pri `sendMessage` start, stop u `finally`. Pattern: 3 pulsa 110/165/247 Hz + sub-oktava 55/82/123 Hz, 700ms pauza, ponavlja. Implementacija: Web Audio API, zero-dep.

## Implementacija

| Element | Lokacija |
|---|---|
| HTML markup | `public/widget.js` (string template, document.body.insertAdjacentHTML) |
| CSS | inline u widget.js (style element) |
| API endpoint | `POST /api/chat` (vidi `app/main.py`) |
| Render | `renderMarkdown()`, `renderProductCard()`, `collapseMultiLineProducts()` |
| Sound | `startThinkingSound()`, `stopThinkingSound()` |

## Embed na webshop — provjera CSP

Webshop možda ima Content-Security-Policy header koji blokira:
- `script-src` mora dozvoliti `aiasistent.bitlab.rs`
- `connect-src` mora dozvoliti `aiasistent.bitlab.rs/api/*`

Ako je striktan, treba dodati exception ili koristiti drugi pristup (proxy widget.js kroz webshop server).
