---
columns:
  - id: todo
    name: Todo
  - id: doing
    name: Doing
  - id: blocked
    name: Blocked
  - id: done
    name: Done
---

# STATUS — bitlab-ai-asistent

Ažurirano: 2026-05-17

Taktički nivo (dnevne taske) prema bitlab-standards shemi
(`bitlab-standards/docs/standards/status-schema.md`). Strateški nivo —
inicijative Now/Next/Later — u [`docs/plans/akcioni-plan.md`](docs/plans/akcioni-plan.md).

**Fokus ove faze: chat-only deploy do produkcije.** Voice i email kanali su
out-of-scope ove faze. DoD: [`docs/plans/dod-chat-only.md`](docs/plans/dod-chat-only.md).

## Todo

- [ ] Voice modul off (chat-only) <!-- id:vmoff -->
  Komentarisati voice import-e i rute (`/api/tts`, `/api/stt`, `/api/voice/status`)
  za chat-only deploy. Ukloniti Whisper init iz `app/main.py:24-39` lifespan-a
  ako ostane nakon komentarisanja. Voice kod ostaje u repu — nije obrisan,
  samo isključen iz aktivnog servisa. Reaktivacija je zaseban korak u kasnijoj
  fazi. Smoke test: chat radi normalno, `/api/voice/status` vraća 404 ili
  eksplicitno disabled. Procjena: 30-60 min. Izvor: DoD sekcija 1.
- [ ] Centralni exception handler za Anthropic API <!-- id:c4xh -->
  Trenutno `app/main.py:59` ima samo `add_exception_handler(RateLimitExceeded, ...)`.
  Nema handler-a za `anthropic.APIStatusError` / `APIConnectionError`. Ako
  Anthropic API ima hiccup ili je kvota potrošena, korisnik dobija HTTP 500 sa
  raw stack trace-om umjesto razumljive poruke. Sub-stavka "nema kredita":
  specifičan slučaj kvota-exhausted (HTTP 429 sa quota error iz Anthropic-a) —
  vrati korisničku poruku različitu od generic rate-limit/server-error poruke,
  jasno saopšti da je kredit potrošen i preusmjeri na ljudsku eskalaciju.
  Posao: `@app.exception_handler(anthropic.APIStatusError)` + `APIConnectionError`
  + quota case discrimination; vrati 503 (ili 402 za quota) sa korisničkom
  porukom; log-uj full trace. Procjena: 30 min. Izvor: DoD sekcija 5.
- [ ] PlaywrightRouter kao test backend <!-- id:pwrt -->
  PlaywrightRouter je interni servis (OpenAI-kompatibilan SDK interfejs) koji
  rutira pozive ka DeepSeek/Claude nalozima (plaćeni i besplatni tier-ovi).
  Postoji prije ove faze. Cilj: postaviti ga kao test backend za masovne eval
  pozive bez produkcijskih troškova. Koraci:
  1. Konfiguracioni sloj (env var ili config flag) da se eval/test pozivi
     rutiraju kroz PlaywrightRouter umjesto direktnog Anthropic SDK-a.
  2. Smoke test — jedan postojeći eval (`evals/run.py`) prolazi kroz
     PlaywrightRouter.
  3. Dokumentovati kako se bira tier (free vs paid) za pojedinačni test set.
  Preduslov za `tst1` Safety net. Izvor: DoD sekcija 4.
- [ ] Strukturisani search output (JSON shema + Pydantic + Layout) <!-- id:srcv -->
  AI output za search rezultate trenutno nije konzistentan — isti tip upita
  može vratiti različite strukture, layout puca na 6-7 rezultata (dokumentovan
  bug "laptopovi do 3000 EUR" u `docs/Otvorena pitanja sa Google Drive-a.md`).
  Trostepena arhitektura:
  1. **JSON shema** — formalna definicija "search result" objekta (polja,
     tipovi, required/optional). Ugovor između AI sloja i UI sloja.
  2. **Pydantic validator** — runtime provjera AI output-a; ne prolazi shemu →
     fail-fast sa jasnom dijagnostikom; ne propagira neispravne podatke u widget.
  3. **Layout** — komponenta u `public/widget.js` koja konzumira validan output
     i prikazuje konzistentno; bez defanzivnih grananja za odsutna polja (jer
     ulaz je garantovan).
  Edge case "prazni rezultati" rješen preko eksplicitnog `empty_state` polja u
  shemi, ne ad-hoc null/prazna lista. Pokriva i FAQ output (`get_faq`) ako shema
  dozvoljava. **Prije nego što napišeš ikakav Pydantic kod**, predloži korisniku
  konkretan JSON schema oblik (polja, required vs optional) i čekaj odobrenje.
  Procjena: 1-2 dana. Izvor: DoD sekcija 2.
- [ ] Hijerarhijske kategorije (parent_id u AI pretrazi) <!-- id:phir -->
  `data/categories.csv` ima `parent_id` polje sa parent-child relacijama
  (513 redova = parent + child). Trenutna pretraga (`app/rag.py`) tretira
  kategorije kao ravnu listu — ne koristi hijerarhiju za klasifikaciju upita
  i ranking rezultata. Koraci:
  1. Učitati parent-child mapu iz CSV-a; izvedeni `data/category_tree.json` ili
     integracija u postojeći `data/categories.json`.
  2. AI tool schema — `search_products` može uzeti `category_id` koji je parent,
     pretraga uključuje i child-ove (i obrnuto, child fallback na parent gdje
     je smisleno).
  3. Migration-drift provjera — neki parent-i imaju 1 proizvod a stvarni
     proizvodi su u child-u (ranije dokumentovano u
     `docs/features/ai-search-improvements.md` "Future work"). Mapiraj drift
     target-e ili drop deprecated parent/child rebalansiraj.
  4. Doc refresh `docs/features/ai-search-improvements.md` — 89→90 kategorija +
     opis hijerarhije (trenutno pominje parent_id samo pod "Future work" linija 258).
  Procjena: 1-2 dana. Izvor: DoD sekcija 3.
- [ ] Safety net + edge case-ovi <!-- id:tst1 -->
  Sistematski sloj testova za ključne tokove i edge ponašanja. Testovi se
  izvršavaju kroz PlaywrightRouter (uslov: `pwrt` aktivan), koristeći DeepSeek
  free tier za masovne CI run-ove. Funkcionalni testovi:
  - Pretraga ponude (RAG) — različiti tipovi upita: brend, kategorija, atribut,
    kombinacija.
  - Pretraga baze znanja (FAQ) — uslovi poslovanja, garancija, dostava i slično.
  - Prompt injection (safety instructions) — otpornost na pokušaje da AI otkrije
    system prompt, mijenja personu, izvršava skrivene instrukcije iz sadržaja
    proizvoda/FAQ-a.
  Edge case ponašanja:
  - Kada provider nema kredita — razumljiva korisnička poruka, ne tehnička
    greška (vezano za `c4xh` handler).
  - Prazni rezultati pretrage — prijedlog alternative, eskalacija ili jasna
    negativna potvrda; ne izmišljeni proizvodi.
  - Nema informacija u bazi znanja — sistem prepoznaje granicu svog znanja i
    eskalira na čovjeka umjesto da izmišlja odgovor.
  Postojeća osnova: `tests/` (7 .py + 1 .mjs), `evals/` (3 runnera),
  `anthropic_api` marker u `pyproject.toml` — proširenje, ne greenfield.
  Procjena: 2-3 dana. Izvor: DoD sekcija 5.

## Doing

## Blocked

## Done

Istorijske kartice — vidi [`docs/archives/status-2026-05-17.md`](docs/archives/status-2026-05-17.md).

## Poznata ograničenja

- ID-jevi kartica (4-8 alfanum) postoje samo zbog `validate-status.py` schema
  validatora — u dijalogu sa korisnikom koriste se naslovi, ne ID.
- Nema lokalnog validatora u repou — shema se provjerava sa
  `bitlab-standards/scripts/validate-status.py`.
- Voice i email su out-of-scope ove faze (chat-only); odgovarajuće inicijative
  su u akcionom planu pod Next.
