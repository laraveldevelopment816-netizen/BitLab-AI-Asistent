---
date: 2026-06-21
branch: feat/ralph-categories-eval
participants: [Ivan Kukić, Claude]
repo: bitLab-ai-asistent
---

# Analiza dizajn paterna iz CMSKP → primjena na BitLab i Asistenta

## Kontekst sesije

Ivan je prepisao stari `cm-scraper-v0` (špageti kod, neodrživ) u novi `cm-scraper` koji koristi
Pipeline, Chain of Responsibility i Factory paterne. Jutros je testirao dva fičera u skafu —
kaže da je nevjerovatno koliko je jednostavno u novom kodu vs stari.

Cilj sesije: duboka analiza šta je promijenjeno i zašto radi bolje → primjeniti iste principe
na BitLab AI Asistenta i ostatak ekosistema.

---

## Turn 1 — Ivan

"Analiziraj dizajn paterne u CMSKP repozitorijumu... pipeline pattern, chain of responsibility,
factory pattern... stari runner.py vs novi... iz dimenzije u dimenziju... primijeni na BitLab i
Asistenta... duboka analiza, ispali subagente, ultra kod, plan mod, jedan MD dokument
design patterns application za bitlaba i asistenta."

## Turn 1 — Claude

Pronašao repo: `/mnt/c/Users/Kule/Projects/compliance-monitoring/`

Struktura:
- `cm-scraper-v0/` — stara verzija (monolitni runner, špageti)
- `cm-scraper/` — nova verzija sa `pipeline/` paketom (Factory, Pipeline, Chain of Responsibility)
- `cm-scraper-v1-cli-pipeline/` — CLI varijanta

Pokrećem workflow sa subagentima: analiza starog koda, analiza novog paterna, analiza BitLab
Asistenta, sinteza i primjena.

---

## Turn 2 — Workflow rezultati (4 subagenta, ~9 minuta)

### Stari kod (cm-scraper-v0) — ključni nalazi

- Arhitektura: layered monolith, ali `haiku/` podsistem narušava granice
- `HaikuBrowserClient`: 438 linija, `wait_for_response()` 160 linija, trofazni state machine
- Fundamentalni anti-pattern: scrape-uje `claude.ai` browser UI umjesto Anthropic SDK
- Duplikat: `_split_into_acts()` identično u `GazettePdfParser` i `PropisiPdfParser`
- `haiku/db_writer.py` vraća `act_type='haiku_parsed'` koji nije u `ActType` enumu

### Novi kod (cm-scraper) — pipeline arhitektura

- **Pipeline**: 7 Stage klasa × ~30 LOC, umjesto monolita
- **Factory**: `build_pipeline()` — jedino mjesto instanciranja Stage-ova
- **Chain of Responsibility**: unutar `RunModelsStage` — modeli se probaju dok jedan ne prođe prag
- **PipelineContext**: jedini objekt koji putuje kroz sve faze
- Dodavanje nove stage: 1 nova klasa + 1 red u `build_pipeline()`

### BitLab AI Asistent — problemi

- **~130 LOC duplikata**: `_run_anthropic()` i `_run_pwr()` rade identičan tool-loop
- **God function**: `run_suite()` u runner.py — 160 LOC, miješa I/O, business logic, HTTP, reporter
- **Module-level side effects**: `tools.py` puni 5 globalnih varijabli pri importu
- **Magic strings**: `'respond_to_user'`, `'category_overview'` hardcoded na više mjesta

### Prioritetni plan refaktoringa

1. **AgentLoop** — protokol za LLM backend, eliminira ~130 LOC duplikata (preduslov za ostalo)
2. **Tool Registry** — `@tool_handler` dekorator, eliminira magic strings i if/elif dispatch
3. **Budget/Cache Pipeline** u `run_suite()` — svaki concern izolovan i testabilan
4. **Lazy tool data** — `CategoryRepository`, testovi mogu injectovati mock bez monkeypatching

### Output fajlovi

- `design-patterns-primjena.md` — 34KB, kompletan dokument sa priručnikom i konkretnim kodom
- `board.html` — živi vizuelni dashboard

---

## Turn 3 — Ivan (vice versa zahtjev)

"Vice versa — analiziraj BitLab i Asistenta, sve što je dobro tamo primijeni na CM Scraper.
Fokus: vektorska baza, Adjenti klub (tool calling/agent pattern), engineer best practices.
CM Scraper je skoro perfektan — samo treba nadograditi."

## Turn 4 — Workflow 2 (5 subagenta, ~6 min)

### Gap analiza CM Scraperа — šta nedostaje

- **Tool Calling**: NEMA. Modeli vraćaju slobodni JSON, post-hoc validacija — fragilno
- **Budget Gate**: NEMA. Može neograničeno pozivati Opus bez praćenja troška
- **Eval Cache**: NEMA. Svaki run zove API iznova (nema SHA-256 kešа)
- **Resume od pale faze**: NEMA. Checkpoint = snapshot za inspekciju, ne za nastavak
- **Vector Search**: NEMA. PDF → direktno u prompt, bez embeddinga

### Šta CM Scraper IMA (ali treba popraviti)

- `stop_after` — implementirano i radi
- `checkpoint` — postoji ali je snapshot-only; + **bug**: run_dir je None u ranim fazama
  (postavlja se tek u SaveStage) pa se checkpoint ne snima kad treba u prethodnim fazama

### Rješenja

**run_dir bug + checkpoint/resume** → **Context Object pattern** (ne Memento, ne Strategy).
`RunContext` nosi: `run_dir`, `completed_stages[]`, `label`, `mode`.
Zna se serijalizovati. run_dir prelazi iz SaveStage u `PipelineContext` constructor.

**Tool Calling** → novi `ToolCallStage` između `BuildPromptStage` i `FinalizeStage`.
Koristi Anthropic `tool_use` API. Opcionalan via `ctx.config.enable_tool_calling`.

**Budget Gate** → port BitLab `budget.py`, pipeline-level wrapper (ne novi stage).

**Hibridna pretraga** → future; za pravne akte embedovati odredbe, ne cijele dokumente.

### Output fajlovi

- `bitlab-dijamanti-cm-scraper.md` — 42KB, kompletan plan implementacije sa Python kodom
- `board.html` — ažuriran sa oba workflowa

---

## Turn 5 — Ivan (force tool calling + duboko istraživanje API-ja)

"Nisi li to napisao da mora da bude force tool calling? Znači to je sad potpuno druga arhitektura,
ne dozvoljavaš modelu da ti vrati ništa osim da poziva nekog od alata. Ajde sad ponovo se baci
na agente i to. I provjeri pored toga šta si još preskočio, šta još ima korisno. Istraži
Entropic API, istraži OpenAI API, šta još ima korisno."

## Turn 5 — Claude

Uočeno: `tool_choice: {"type": "any"}` u dokumentu bio ugrađen u code block, nije istaknuto
kao arhitekturna odluka. Dodat novi sadržaj u `bitlab-dijamanti-cm-scraper.md`:

1. **Četiri nova one-linera** na vrhu — Force Tool Calling, Prompt Caching, Batch API, Extended Thinking
2. **Sekcija 7 — Force Tool Calling kao Arhitekturna Odluka**: dijagram stare vs nove arhitekture, PWR podrška (`schemas.py:212`), concrete `COMPLIANCE_TOOL` definicija
3. **Sekcija 8 — Prompt Caching**: `cache_control: ephemeral`, kalkulacija uštede (90%), `BuildPromptStage` integracija
4. **Sekcija 9 — Batch API**: `POST /v1/messages/batches`, 50% cijenovna redukcija, polling pattern, `BatchRunnerStage` koncept
5. **Sekcija 10 — Extended/Adaptive Thinking**: proširena Chain of Responsibility, `thinking: {type: "adaptive"}` bez `budget_tokens`

---

## Turn 6 — Ivan (reorganizacija + zatvaranje sesije)

"Premjesti dokumente u root repo-a. Design patterns primjena u BitLab root, BitLab dijamanti u
CM Scraper root. U brainstormu ostaju samo board i log. Komitaj i pusaj na oba repozitorija,
na CM Scraper prvo pull."

## Turn 6 — Claude

Reorganizacija i push:

- `design-patterns-primjena.md` → `/mnt/c/Users/Kule/Projects/bitLab-ai-asistent/`
- `bitlab-dijamanti-cm-scraper.md` → `/mnt/c/Users/Kule/Projects/compliance-monitoring/cm-scraper/`
- Brainstorm folder: ostali samo `board.html` i `log.md`

CM Scraper: `git pull` povukao 282 novih linija (factory, CLI, unit testovi) → commit + push na `staging`.
BitLab: commit + push na `feat/ralph-categories-eval`.

---

## Zaključak sesije

**Datum:** 2026-06-21  
**Trajanje:** ~1h 30min  
**Output:** 2 dokumenta, ukupno ~2 900 linija analize i Python koda

### Šta je urađeno

**Smjer 1 — CMSKP paterne → BitLab Asistent** (`design-patterns-primjena.md`):
Identifikovane su četiri prioritetne intervencije: AgentLoop protokol koji eliminiše ~130 LOC duplikata između `_run_anthropic()` i `_run_pwr()`, Tool Registry koji zamjenjuje magic strings i if/elif dispatch, Budget/Cache pipeline koji izoluje svaki concern u `run_suite()`, i Lazy tool data koji omogućava mock injection bez monkeypatching-a.

**Smjer 2 — BitLab dijamanti → CM Scraper** (`bitlab-dijamanti-cm-scraper.md`):
Deset dijamanta preslikana na CM Scraper pipeline sa konkretnim Python kodom i prioritetnim roadmapom. Ključni nalazi: arhitekturni bug `run_dir=None` u ranim fazama (rješava Context Object pattern), fragilni `validiraj_json()` koji nestaje s force tool calling-om, plus četiri nova API feature-a koja CM Scraper uopće ne koristi — Prompt Caching (90% ušteda na statičkim promptovima), Batch API (50% jeftinije za voluminoznu obradu), Force Tool Calling kao arhitekturna garancija (PWR već podržava), i Adaptive Thinking kao posljednji fallback u chain-u.

### Ključni insight sesije

Razlika između starog i novog CM Scraper-a Ivan je opisao kao "iz pakla u raj" — što direktno mapira na poentu sesije: loose coupling i pipeline arhitektura nisu samo estetika, nego preduslov da možeš uopće testirati, mijenjati i nadograđivati sistem. BitLab Asistent je taj raj kojeg CM Scraper tek treba dostići.

### Sljedeći koraci (za implementaciju)

1. Mock seam u `providers.py` — preduslov za sve ostalo
2. `PipelineRunContext` + `run_dir` fix
3. `ToolCallStage` sa `tool_choice: {"type": "any"}`
4. `cache_control: ephemeral` na sistem promptu (`BuildPromptStage`)
5. Batch API CLI komanda za voluminozne runove
