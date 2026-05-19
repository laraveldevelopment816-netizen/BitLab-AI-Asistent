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

Ažurirano: 2026-05-19

Taktički nivo (dnevne taske) prema bitlab-standards shemi
(`bitlab-standards/docs/standards/status-schema.md`). Strateški nivo —
inicijative Now/Next/Later — u [`docs/plans/akcioni-plan.md`](docs/plans/akcioni-plan.md).

**Fokus ove faze: chat-only deploy do produkcije.** Voice i email kanali su
out-of-scope ove faze. DoD: [`docs/plans/dod-chat-only.md`](docs/plans/dod-chat-only.md).

## Todo

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

- [ ] PWR backend za chat agent + test eval (LLM_BACKEND=anthropic|pwr) <!-- id:pwrt -->
  Preostalo do Done:
  1. Ažurirati sistem prompt da Claude emituje strukturisani output prema
     `app/schemas.py` shemi i uvijek vraća isti shape (products / empty /
     message).
  2. Aplicirati Pydantic validator (`schemas.TypeAdapter`) na AI output na
     izlazu iz `run_agent` — fail-fast ako shape nije validan.
  3. Manuelno testiranje preko PWR puta sa različitim upitima (chat / email /
     voice kanali).
  4. Popraviti pad-ove iz [`TEST-failures-pwr-migration.md`](TEST-failures-pwr-migration.md).
  5. Deploy na staging i smoke test produkcijskog puta.

  Urađeno do sada:
  Feature flag u `app/config.py` (`LLM_BACKEND`, default `anthropic` — produkcija
  nepromijenjena; `pwr` rutira kroz PlaywrightRouter na `http://127.0.0.1:8765/v1`).
  `app/agent.py` razdvojen na `_run_anthropic` i `_run_pwr` loop-ove; PWR put koristi
  `openai.OpenAI` SDK, mapira `finish_reason="tool_calls"` na isti dispatch kao
  Anthropic `tool_use`. `_trace` nosi novi `via_pwr` flag (UI prikaže "paušal" mjesto
  cijene). `app/tools.py` dobio `ALL_TOOLS_OPENAI_SHAPE` (čista derivacija iz
  `ALL_TOOLS`) + dedup za `escalate_to_human` (SHA(reason|summary), 5-min TTL) da PWR
  retry ne pošalje dupli email. `openai>=1.50` dodato u `pyproject.toml`.

  DoD verifikacija (kod-nivo, prije manuelnog testiranja):
  - pytest 106/106 prolazi sa default `LLM_BACKEND=anthropic`, 0 regresija.
  - Anthropic produkcijski put nepromijenjen — live test sa "laptop do 1500 KM"
    pravilno trigger-uje `search_products(category_id=98, max_price_km=1500)`.
  - PWR category accuracy: 40/41 = **97.6%** (threshold 85%, baseline ~95-100%).
  - PWR HTTP eval na `test_questions.json`: 19/20 = **95%** (threshold 80%).
  - Voice channel collision: 0/5 ⟦tool_use⟧ leak-ova u `<voice>/<text>` blokovima
    (Risk #1 iz brief-a verificiran clean).

  Working tree (nekomitovan):
  - `app/agent.py` +178 net (dispečer + `_run_pwr` + `via_pwr` u helper-ima)
  - `app/config.py` +28 net (feature flag + PWR settings + cross-field validator)
  - `app/tools.py` +40 net (OpenAI shape + escalation dedup)
  - `pyproject.toml` +3 (openai dep)
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
- [ ] Per-channel model + effort iz .env (Anthropic + PWR) <!-- id:mdef -->
  Override modela i effort-a po kanalu kroz `.env`, hirurški. Voice kanal
  dijeli model sa chat (nije zasebno polje). `CHAT_MODEL`/`EMAIL_MODEL` su
  već auto-mapirani preko pydantic-settings (`app/config.py:35-36`), samo
  zakomentarisani u `.env.example`; PWR ekvivalenti (`pwr_chat_model`/
  `pwr_email_model`) postoje u config-u ali nisu dokumentovani u .env.example.
  Koraci:
  1. `app/config.py` — dodati 4 nova polja: `chat_effort`, `email_effort`
     (Anthropic, mapiranje kao i postojeće — thinking budget) +
     `pwr_chat_effort`, `pwr_email_effort` (Literal `"low"|"medium"|"high"`,
     default `"medium"`). Postojeća model polja se ne diraju.
  2. `app/agent.py` — proslijediti effort u API poziv u `_run_anthropic`
     (thinking budget kao trenutno) i `_run_pwr` (`reasoning_effort` kwarg
     OpenAI SDK-a). Bez drugih izmjena u API callsite-ovima.
  3. `.env.example` — odkomentarisati postojeći Anthropic blok + dodati
     PWR blok: `CHAT_MODEL`, `CHAT_MODEL_EFFORT`, `EMAIL_MODEL`,
     `EMAIL_MODEL_EFFORT`, `PWR_CHAT_MODEL`, `PWR_CHAT_MODEL_EFFORT`,
     `PWR_EMAIL_MODEL`, `PWR_EMAIL_MODEL_EFFORT`.
  4. Smoke: pytest 106/106 + jedan curl po backendu da effort stigne do
     trace log-a.

  Princip: postojeći default-i u `config.py` ostaju netaknuti, Anthropic
  produkcijski put nepromijenjen za default vrijednosti. Procjena: pola dana.

## Blocked

## Done

- [x] Centralni exception handler za Anthropic API <!-- id:c4xh -->
  `app/main.py` sad registruje `@app.exception_handler` za
  `anthropic.APIStatusError` i `anthropic.APIConnectionError` — safety net za
  greške koje `app/agent.py` ne uhvati lokalno (Auth/Permission/Internal/itd.).
  Quota discrimination po "credit balance"/"billing"/"quota" tekstu u poruci →
  HTTP 402 + telefon/email eskalacija. Ostale API greške → HTTP 503 + generička
  poruka. Mrežne greške → HTTP 503 + poruka o mreži. Full trace se loguje sa
  `exc_info=True` na `logger.error`. Widget (`public/widget.js`) ažuriran da
  čita `data.reply` i na non-200 odgovorima, tako da korisnik vidi specifičnu
  poruku umjesto generičkog "Greška servera". Pokriveno sa
  [`tests/test_anthropic_error_handlers.py`](tests/test_anthropic_error_handlers.py)
  (7 testova: AuthError, InternalServerError, kvota varijante credit_balance/
  billing/quota, ConnectionError, happy path regression) — svi prolaze, ne
  troše pravi API. Plan ručnog testa (uživo curl + browser widget render):
  [`TEST-anthropic-errors.md`](TEST-anthropic-errors.md).
- [x] Voice modul off (chat-only) <!-- id:vmoff -->
  Backend: dekoratori `/api/tts`, `/api/stt`, `/api/voice/status` komentarisani
  u `app/main.py` (funkcije ostaju za reaktivaciju), "Whisper" leftover uklonjen
  iz lifespan komentara. Frontend: `VOICE_ENABLED=false` u `public/widget.js` —
  pre-flight fetch ka `/api/voice/status` se ne izvršava, mikrofon button
  ostaje hidden, nema 404 spam-a u Network tab-u. Smoke test prošao na portu
  7777 (8000-8090 zauzeti na WSL-u): startup log čist, `/api/chat` HTTP 200,
  tri voice rute HTTP 404, `/healthz` OK. Plan testa i koraci za reaktivaciju:
  [`docs/how-to-test/TEST-voice-off.md`](docs/how-to-test/TEST-voice-off.md).

Istorijske kartice — vidi [`docs/archives/status-2026-05-17.md`](docs/archives/status-2026-05-17.md).

## Poznata ograničenja

- ID-jevi kartica (4-8 alfanum) postoje samo zbog `validate-status.py` schema
  validatora — u dijalogu sa korisnikom koriste se naslovi, ne ID.
- Nema lokalnog validatora u repou — shema se provjerava sa
  `bitlab-standards/scripts/validate-status.py`.
- Voice i email su out-of-scope ove faze (chat-only); odgovarajuće inicijative
  su u akcionom planu pod Next.
