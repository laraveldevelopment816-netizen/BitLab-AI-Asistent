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

- [ ] Pun model ID svuda u dashboard-u (ukloni "haiku/sonnet/opus" skraćenice) <!-- id:fmnm -->
  Dashboard koristi `_short_model_name` (`app/server/dashboard.py:702`) koji
  mapira pun model ID na 3-slovne skraćenice ("haiku"/"sonnet"/"opus"). Te
  skraćenice se koriste kao:
  - Adapter label (`chat:sonnet`) u DB `requests.adapter` koloni.
  - `model_registry` ključevi (`app/config.py:136-139`) — `{"haiku": chat_model,
    "sonnet": email_model}` — eksposed kao `/api/dashboard/compare` API ugovor.
  - Frontend categorization (`dashboard/src/tokens.ts:30-32` MODEL color map,
    plus `History.tsx`/`RequestDetail.tsx`/`SessionDetail.tsx` substring matcher-i).
  Per PWR `models-and-efforts.md` § 3.1, "Opus"/"Sonnet" labele su rezervisane
  za web chat variant picker (`pwr_options.claude_variant="Opus 4.7"`) — BAA
  treba referencirati pun explicit ID svuda da se izbjegne semantička kolizija.
  Koraci:
  1. Backend — ukloni `_short_model_name`, propagiraj pun model ID u adapter
     label (`chat:claude-sonnet-4-6` umjesto `chat:sonnet`).
  2. `model_registry` — ključ promijeni iz `"haiku"`/`"sonnet"` u pun ID
     (`claude-haiku-4-5-20251001`/`claude-sonnet-4-6`); update `/compare`
     endpoint dokumentaciju.
  3. DB migracija — postojeći `requests.adapter` redovi ostaju (read-only
     istorija), novi insertovi koriste pun ID.
  4. Frontend — `tokens.ts` MODEL color map keys + ostali substring matcher-i.
  5. Smoke: dashboard renderuje boje za nove labele, `/compare` prihvata pun
     ID, postojeće sesije i dalje vidljive.

  Procjena: 0.5 dan (backend) + 0.5 dan (frontend) = 1 dan. Izvor: posljedica
  mdef rename-a + standardizacija reference na model po PWR docs § 3.1.
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

## Blocked

## Done

- [x] Per-channel model + effort iz .env (Anthropic + PWR) <!-- id:mdef -->
  `app/config.py:41-56` ima 4 nova polja (`chat_model_effort`, `email_model_effort`,
  `pwr_chat_model_effort`, `pwr_email_model_effort`) tipa Literal
  `"low"|"medium"|"high"`, default `"low"`. `app/agent.py:162-251` propagira
  effort kroz `_default_effort_for_channel`, `_anthropic_thinking_kwargs`
  (mapira na Anthropic extended thinking budget) i kroz `reasoning_effort`
  kwarg u `_run_pwr`. `.env.example:5-26` dokumentuje sva 4 EFFORT polja sa
  komentarima. Effort se persistuje u novoj `requests.effort` koloni (additive
  ALTER u `app/storage/db.py`) i izložen je kroz dashboard API
  (`RequestRow.effort`, `RequestDetail.effort`) u tabelama i detalj-stranama
  UI-ja. Anthropic produkcijski put nepromijenjen za default `"low"` (vraća
  prazan thinking kwargs). Plan ručnog testa:
  [`TEST-channel-model-effort.md`](TEST-channel-model-effort.md) (working
  tree, uncommitted).
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
