---
sections:
  - id: now
    name: Now
  - id: next
    name: Next
  - id: later
    name: Later
  - id: completed
    name: Completed
---

# Akcioni plan — bitlab-ai-asistent

Ažurirano: 2026-05-17

> Strateški plan (Now/Next/Later inicijative) za `bitlab-ai-asistent`.
> Schema: [`bitlab-standards/docs/standards/akcioni-plan-schema.md`](../../../bitlab-standards/docs/standards/akcioni-plan-schema.md).
> Taktički nivo (dnevne taske) — [`../../STATUS.md`](../../STATUS.md).

**Fokus ove faze: chat-only deploy do produkcije.** Voice i email kanali
su out-of-scope ove faze. DoD: [`dod-chat-only.md`](dod-chat-only.md).

## Now

### Voice modul off <!-- id:vmoff -->

Voice komponente (TTS, STT, voice status endpoint) ne učitavaju se pri
startu aplikacije. Import-i i pripadajuće rute komentarisani; Whisper
init uklonjen iz lifespan-a. Voice kod ostaje u repu — nije obrisan,
samo isključen iz aktivnog servisa.

Taske: [`STATUS.md`](../../STATUS.md) — Todo kartica "Voice modul off".

### Strukturisani search output <!-- id:srcv -->

Trostepena arhitektura: JSON shema (ugovor) + Pydantic validator
(fail-fast u agent loop-u) + widget layout (deterministički, bez
defanzivnih grananja). Eliminacija klase bug-ova vezanih za
inkonzistentne AI odgovore (layout pucanje na 6-7 rezultata,
neočekivane strukture). Edge case "prazni rezultati" rješen preko
`empty_state` polja u shemi.

Taske: [`STATUS.md`](../../STATUS.md) — Todo kartica "Strukturisani search output".

### Hijerarhijske kategorije <!-- id:phir -->

AI pretraga koristi `parent_id` parent-child strukturu iz
`data/categories.csv`. Klasifikacija upita i ranking uzimaju
hijerarhiju u obzir (trenutno tretira ravno). Doc refresh
`docs/features/ai-search-improvements.md` završetak — 89→90 kategorija
+ opis hijerarhije.

Taske: [`STATUS.md`](../../STATUS.md) — Todo kartica "Hijerarhijske kategorije".

### PlaywrightRouter kao test backend <!-- id:pwrt -->

PlaywrightRouter (interni servis, OpenAI-kompatibilan SDK) rutira test
pozive ka DeepSeek/Claude tier-ovima (plaćeni i besplatni). Eval i
safety net testovi koriste ga umjesto skupih Anthropic API poziva —
masovni run-ovi u CI-ju ekonomski održivi.

Preduslov za Safety net + edge cases inicijativu.

Taske: [`STATUS.md`](../../STATUS.md) — Todo kartica "PlaywrightRouter kao test backend".

### Exception handler za Anthropic API <!-- id:c4xh -->

Centralni handler za `anthropic.APIStatusError`, `APIConnectionError` i
specifičan slučaj **"nema kredita"** (kvota potrošena). Korisnik dobija
razumljivu poruku različitu od generic rate-limit/server-error poruke,
sa eskalacijom na čovjeka kad je kredit potrošen.

Taske: [`STATUS.md`](../../STATUS.md) — Todo kartica "Centralni exception handler".

### Safety net + edge case-ovi <!-- id:tst1 -->

Sistematski testovi pokrivaju ključne tokove i edge ponašanja:
- **Funkcionalni**: pretraga ponude (RAG), pretraga baze znanja (FAQ),
  prompt injection (safety instructions).
- **Edge cases**: kada provider nema kredita, prazni rezultati pretrage,
  nema informacija u bazi znanja → eskalacija na čovjeka.

Testovi se izvršavaju kroz PlaywrightRouter (uslov: `pwrt` aktivan),
koristeći DeepSeek free tier za masovne CI run-ove.

Taske: [`STATUS.md`](../../STATUS.md) — Todo kartica "Safety net + edge case-ovi".

## Next

### Email autoreply (osnovni + hybrid AI) <!-- id:mail1 -->

n8n autoreply za webshop inbox. Keyword filter za jasne slučajeve
(predefinisani odgovori). AI fallback za nejasne upite: Haiku 4.5 prvi
pass; eskalacija na Sonnet 4.6 za nijansirane B2B/komplikovane upite.
Cost estimate ~$5-15/mjesec sa keyword pre-filterom.

Preduslov: DNS riješen (završeno — Rale, 2026-05-16). Čeka Branislav-ove
kredencijale + smoke test.

### Eval framework full <!-- id:evl1 -->

Multi-provider eval framework kroz PlaywrightRouter abstraction.
Pokrivanje: edge case-ovi van DoD safety net-a, multi-model komparacija
(DeepSeek/Claude varijante), best-practice struktura (verzionisani
golden datasetovi, prag po metrici, automatizovani CI run sa
regresijskim signalom).

PlaywrightRouter već čini multi-provider abstraction — ova inicijativa
se svodi na definisanje eval scenarija i automatizaciju, ne na izgradnju
gateway-a.

### Operativna higijena <!-- id:ops1 -->

- **Drugi prolaz reorganizacije**: extract iz
  `docs/Otvorena pitanja sa Google Drive-a.md` — manuelna procjena po
  stavci (UX bugovi → STATUS Todo, ops zahtjevi → nove kartice, ostatak
  arhivirati). 4 embedded base64 png-a izvući kao zasebne fajlove ili
  arhivirati zajedno.
- **Stale doc cleanup**: `docs/reviews/security-review.md` body i dalje
  piše "🔓 OTVORENO" za V2/V3/S1/S2/S3/N2/N3 iako su zatvoreni. Slično
  cleanup za stale reference u drugim doc-ovima ako se otkriju.
- **Defensive lock-ovi**: `threading.Lock` (double-checked) u 3 lazy
  helpera (`app/rag.py:436`, `app/agent.py:57`, `app/tools.py:230`).
  Low real risk — race window samo na startup-u prvog requesta;
  `lifespan` mitigates za `_index`, ne za druga dva.

## Later

### bitlab-standards adopcija <!-- id:std1 -->

Usklađivanje doc strukture, ID konvencija i validacijskih skripti sa
bitlab-standards SSOT repository. `docs/README.md` linkuje nazad na
bitlab-standards. Sekundarno — nije production-blocker, proces meta.

## Completed

Istorijske inicijative (MVP, Sesija 6 n8n deploy, Sesija 7 polish,
Sesija 8 dashboard, LIVE test 2026-05-08, AI search brand+category
improvements, git/standards konsolidacija, P2 cold-start, dorg prvi
prolaz reorganizacije, arch konsolidacija arhive, LIVE.md rastavak,
scan.sh tooling) — vidi
[`../archives/akcioni-plan-2026-05-17.md`](../archives/akcioni-plan-2026-05-17.md)
i [`../archives/status-2026-05-17.md`](../archives/status-2026-05-17.md).
