---
date: 2026-05-20
branch: staging
participants: [Kule, Claude]
topic: Parent kategorije na BitLab AI asistent sistemu — vizualizacija, dodavanje na parent, pretraga po parent kategoriji
---

# Log — 2026-05-20 — bitlab-parent-kategorije

## Kontekst

Brainstorm o parent kategorijama u BitLab AI asistent sistemu. Tri aspekta:
1. Vizualizacija parent kategorija.
2. Dodavanje (pridruživanje) na parent kategoriju.
3. Pretraga po parent kategoriji u search sistemu.

## Transkript

### Korisnik je pokrenuo `evals/visualize_parent_expansion.py` i ne zna kako da pročita izlazni HTML

Skripta je iz `bitlab-ai-asistent/evals/visualize_parent_expansion.py` (ne `test_e2e_visual.py` — to je drugi alat, CLI E2E tester za `/api/chat`).

**Šta skripta radi:**
- Deterministički before/after vizualizator za parent_id expansion fix u `app/rag.py`. Bez LLM-a, bez servera, bez embedding indeksa.
- Skenira `data/categories.csv` (active cats) i `data/all-products.json`.
- Inspektuje `app/rag.py` da odluči da li je fix već primijenjen — tri heuristike: helper `_load_cat_descendants` postoji, polje `self._cat_descendants` se inicijalizuje, filter koristi set membership umjesto `==`.
- Generiše `~/Downloads/parent-expansion-{YYYYMMDD-HHMMSS}.html`.

**Ključni pojmovi u izlaznom HTML-u:**
- `direct` — broj proizvoda koje equality filter (`categories_id == cat_id`) vidi za taj cat. Mala brojka za root-ove sa puno djece.
- `subtree` — broj proizvoda u cat-u + svih descendant-a (set membership filter). Velika brojka za root-ove.
- `current` — STVARNA produkcijska brojka koju search trenutno vraća. Zavisi od `fix_applied`:
  - Bez fix-a → `current = direct` (mala).
  - Sa fix-om → `current = subtree` (velika).
- `alternative` — hipotetička brojka u drugom modu (poredbeni broj "bilo bi").
- `delta = subtree - direct` — potencijalni gain ako se fix primijeni, ili realizovani gain ako jeste.
- `coverage_pct` — koliko subtree pool-a current mode pokriva.
- Verdict: PASS (≥ threshold % coverage), FAIL (< threshold), NA (leaf).

**Primjer cat 17 (Računari):**
- BEFORE fix: `current = 20` (samo proizvodi direktno na cat 17).
- AFTER fix: `current = 197` (cat 17 + svi Notebook/Tablet/Desktop child cat-ovi).
- Delta = +177.

**HTML strukture:**
1. Verdict banner (top) — zeleno PASS ili crveno FAIL. Pokazuje i evidence iz `rag.py` (3 provjere).
2. Stats kartice — total products, root cats, Σ root pool current, Σ root pool alternative, # FAIL parents, # PASS parents.
3. Leaderboard tabela — top 15 root cat-ova po delti, sa bar chart-om.
4. Full tree — hijerarhijski svi cat-ovi, sortirano po delti, sa filterima (Sve / Samo FAIL / Leaf).

**Sljedeći korak u sesiji:** korisnik je pitao kako da čita fajl; predloženo je hodati kroz sekcije redom (banner → stats → leaderboard → tree).

### Stvarna podaci iz user-ovog HTML-a (`parent-expansion-20260520-154321.html`)

Otvoren direktno sa file system-a (bitlab-ai-asistent root). Parsed kroz Python ekstrakciju DATA constanta:

- **Fix state: applied = true** (sve 3 heuristike YES). PASS banner zeleno.
- 5287 ukupno proizvoda, 238 aktivnih cat-ova, 41 root cat-ova.
- **Σ current = 4634** kroz root upite (sa fix-om).
- **Σ alternative = 301** (bilo bi bez fix-a). Delta = +4333.
- 28 PASS parents, 1 FAIL parent (još uvijek ispod threshold-a — koji nismo identifikovali u sesiji).
- Top 5 leaderboard po delti:
  1. cat 151 Mobiteli: 1575 vs 5 (+1570).
  2. cat 219 PC periferija: 638 vs 0 (+638).
  3. cat 341 Potrošni materijal: 300 vs 0.
  4. cat 356 Kablovi i adapteri: 280 vs 0.
  5. cat 107 PC komponente: 255 vs 0.
- cat 17 Računari je tek 7. po impactu (+177), ne 1. — što je u suprotnosti sa fokusom na cat 17 u docstring-u skripte (vjerovatno odabran kao didaktički primjer, ne kao primarni motivator fix-a).

### Branch realnost: fix je SAMO na feature granu

Korisnik je sumnjao da je report rađen na nekoj specifičnoj grani — to je tačno. Provjereno:

- `bitlab-ai-asistent` trenutni branch: `claude/analyze-category-hierarchy-dIVqm` (fix prisutan, PASS).
- `staging` branch: **NEMA** ni `_load_cat_descendants` ni set membership filter — search radi po starom equality modu.
- `main` branch: isto, **NEMA** fix.

**Implikacija na production:** ako se na staging-u ukuca pretraga za "PC periferija" → 0 proizvoda. "Mobiteli" → 5. "Računari" → 20. Velike brojke iz leaderboard-a dolaze tek nakon merge-a feature grane u staging.

User je svjesno odlučio da fokus ne bude na merge tog brancha — pomjerio temu na drugi incident.

### Incident: staging.aiasistent.bitlab.rs pao (502 Bad Gateway)

Curl iz lokalnog WSL-a pokazao HTTP 502 — nginx živ, upstream port 8001 (FastAPI staging) mrtav.

User-ov recall: zbog manjka memorije na VPS-u ranije su ručno stopirani memory-heavy servisi:

- `n8n-prod.service` (port 8030, ~800 MB)
- `n8n-staging.service` (port 8031, ~800 MB)
- `aiasistent-staging.service` (port 8001, ~600 MB)
- Vjerovatno još nešto za Chrome login (Playwright Router?) — nije u bitlab-ai-asistent deploy folderu, sibling repo.

Stop je bio namjeran, ali zaboravili su vratiti.

**Workflow correction (zapisana u memory):** user pokreće sve server komande sam — Claude ne nudi da pokreće, ni za read-only diagnostike. Workflow je `scripts/cmd.sh "<command>"` za click-to-copy u dictate panel; user runa i paste-uje output. Memory fajl: `feedback_no_server_changes_without_approval.md` ažuriran sa Voice-mode addendum-om.

**Dvije cmd komande pripremljene u dictate panelu:**

1. `sudo systemctl list-units --type=service --state=inactive,failed --no-pager`
2. `sudo systemctl start aiasistent-staging`

### Doc gap → novi runbook

Dokumentacija za upravljanje servisima na serveru nije postojala. Najbliže: `bitlab-ai-asistent/deploy/RUNBOOK-prod.md`, ali to je samo za inicijalni setup prod-a, ne za status / start / stop / logs / recovery.

Napravljen novi fajl: `bitlab-ai-asistent/deploy/RUNBOOK-services.md`.

Sadrži:
- Tabelu servisa (port, domain, RAM, svrha).
- Status komande (list-units, status, ss -tlnp, memorija po servisu).
- Start / stop / restart (pojedinačno + bulk).
- Logs (journalctl -n / -f / grep error).
- Health checks iz lokalnog WSL-a (curl healthz svih domena).
- Memorija na serveru (free -m, ps --sort=-rss).
- Nginx reload + restart.
- Incident recovery template za "staging pao zbog memorije".
- TODO: Chrome login (Playwright Router) servis, SSL cert renewal, n8n encryption key reset.

Svaka komanda u zasebnom code blocku → kompatibilno sa click-to-copy.

### Paradoks: staging vraća rezultate za "PC periferija" iako fix nije primijenjen

User je empirijski testirao na staging-u — ukucao "PC periferija" i dobio: miš gaming Trivi, GM Titanium 4 tastature, podloge, slušalice, USB hubove. Pitao kako je to moguće ako staging nema fix?

**Odgovor: parent fix se odnosi SAMO na hard filter scenario.** Staging vraća rezultate kroz tri nezavisna mehanizma koji ne ovise o `descendants` set-u:

1. **Hibridna pretraga bez category_id hard filtera** (`app/rag.py` linije 322–328 na staging):
   - `search_products` tool može biti pozvan BEZ `category_id` parametra.
   - Onda BM25 + vektorski embeddings (sentence-transformers `all-MiniLM-L6-v2` ili sl.) prolaze kroz svih 5287 proizvoda i rangiraju po fusion score (0.6 vektor + 0.4 BM25).
   - Embedding "PC periferija" je u vektorskom prostoru blizu "miš", "tastatura", "podloga za miš", "USB hub" → ovi rezultati prirodno izlaze gore.

2. **LLM kao smart router** (`app/tools.py` linije 64–80):
   - Tool description-u eksplicitno daje Claude-u listu svih kategorija sa labelama i pravila klasifikacije: "Brand-only — popuni `brand_id` ali pusti `category_id` prazan".
   - Claude može vidjeti "PC periferija" je parent (cat 219) i odlučiti da NE pošalje `category_id`, već da pusti hibridnu pretragu, ILI da pošalje child cat (npr. 277=miševi).
   - Zato u praksi user rijetko vidi nule — Claude izbjegava parent kao hard filter.

3. **Soft category boost** (`app/rag.py` linije 339–347, `_detect_intent_categories`):
   - Ako `category_id` nije proslijeđen, sistem tokenizuje query, mapira preko `category_terms.json`, i DODAJE +0.25 score boost svim proizvodima u tih kategorija.
   - To je samo boost ranga, ne hard filter — produkti se ne odbacuju, samo se podižu.
   - Ako se "PC periferija" mapira na cat 219, boost se primjenjuje na proizvode čiji `categories_id == 219` — ali to su nula proizvoda (svi su u djeci), pa konkretno ovaj boost ne pomaže za parent. Pomogao bi za "miš" → cat 277 → ima 200+ proizvoda → boost radi.

**Kad parent fix STVARNO postaje važan:**
- Eksplicitan tool call sa `category_id=<parent_cat_id>` (npr. ako Claude pogriješi i pošalje cat 219).
- Internal flows koji koriste hard filter direktno (npr. budući "kategorijski browse" endpoint).
- Sigurnosna mreža — ako Claude promijeni ponašanje, fix garantuje da hard filter za parent neće dati 0.

Zaključak: fix ne dolazi do izražaja u tipičnom UX scenario-u jer Claude zaobilazi problem na LLM sloju. Fix je više defensive depth — pokriva edge case kad neko ipak pošalje parent kao filter.

### Sljedeći korak: E2E test svih parent kategorija

User želi da empirijski vidi šta Claude RADI za svaku parent kategoriju iz leaderboard-a, sa stvarnim tool_call argumentima i stvarno vraćenim proizvodima — paralelno sa leaderboard delta brojkama.

**Otkriće:** alat već postoji — `evals/run_e2e_html.py` (845 linija). Pokreće pun agent loop preko `/api/chat`, parsira proizvode iz Claude reply-ja, mapira ih na njihov `categories_id` iz `all-products.json`, i renderuje HTML sa routing drift + result drift overlay na parent_id stablu.

Razlika od `run_categories_html.py`: ovaj koristi `claude` CLI sa JSON instrukcijom (samo klasifikacija); `run_e2e_html.py` ide pun agent loop preko HTTP.

**Pripremljeno:** `evals/parent_eval_set.json` — 15 upita, svaki je doslovno ime parent kategorije iz leaderboard-a:

| # | Query                              | Cat ID | Leaderboard delta |
|---|------------------------------------|--------|-------------------|
| 1 | Mobiteli                           | 151    | +1570             |
| 2 | PC periferija                      | 219    | +638              |
| 3 | Potrošni materijal                 | 341    | +300              |
| 4 | Kablovi i adapteri                 | 356    | +280              |
| 5 | PC komponente                      | 107    | +255              |
| 6 | Mrežna oprema                      | 352    | +203              |
| 7 | Računari                           | 17     | +177              |
| 8 | Televizori i prateća oprema        | 148    | +169              |
| 9 | Kancelarijski materijal            | 214    | +145              |
| 10| USB uređaji                        | 347    | +123              |
| 11| Satovi                             | 152    | +99               |
| 12| Baterije i punjači                 | 160    | +88               |
| 13| USB stickovi i memorijske kartice  | 346    | +57               |
| 14| Fotoaparati i camcorderi           | 150    | +40               |
| 15| Mediji                             | 227    | +35               |

**Komanda za pokretanje** (lokalno, server na :7778):
```bash
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent && \
  python evals/run_e2e_html.py --queries evals/parent_eval_set.json --url http://127.0.0.1:7778
```

Output: `docs/category-analysis/e2e-run-latest.html`.

**Open question:** ide li i companion skript koji sortira rezultate side-by-side sa leaderboard delta-om (tabela: query → Claude tool_call → vraćeni proizvodi count → očekivana delta → da li se LLM "snalazi" čak i bez fix-a)? Tek-čekano user odluku.

### Odluka: napraviti runtime visualizer u istom UI stilu

User je rekao DA — napraviti companion skript sa identičnim UI šelom kao `visualize_parent_expansion.py` (dark theme, verdict banner, stats kartice, leaderboard, expandable detalji), ali punjen runtime podacima.

**Napravljeno:** `bitlab-ai-asistent/evals/visualize_parent_runtime.py` (~400 linija).

Logika:
- Za svaki upit iz `parent_eval_set.json` napravi POST na `{url}/api/chat`.
- Iz response-a izvuče: `reply`, `tool_calls`, `tools_used`, `iterations`.
- Parsira proizvode iz reply-ja (markdown PROD_RE iz `test_e2e_visual.py`).
- Mapira svaki proizvod na njegov `categories_id` preko `data/all-products.json` lookup-a.
- Računa: koja kategorija je rutovana (iz prvog `search_products` poziva), koliko proizvoda je vraćeno, koliko od tih je u expected subtree.

**Verdicts:**

| Routing       | Značenje                                                     |
|---------------|--------------------------------------------------------------|
| `EXACT_PARENT`| Claude poslao baš parent cat_id — najopasniji case za BEFORE staging |
| `DESCENDANT`  | Claude poslao child cat unutar subtree — smart routing       |
| `NULL`        | Claude nije poslao filter — pusto za hybrid + soft boost     |
| `OUT`         | Claude poslao kategoriju van subtree — promašaj              |

| Result | Threshold                                                       |
|--------|-----------------------------------------------------------------|
| `PASS` | ≥ 3 proizvoda u expected subtree                                |
| `WARN` | 1–2 proizvoda u expected subtree                                |
| `FAIL` | 0 proizvoda u expected subtree, ili 0 vraćeno uopšte            |

**Versioning:** `--label v1` / `--label v2-prompt-tweak` ide u filename. Output: `~/Downloads/parent-runtime-{label}-{TS}.html`. Tako se regression compare radi otvaranjem dva fajla side-by-side.

**Komande u dictate panelu:**
1. Smoke test (3 upita): `python evals/visualize_parent_runtime.py --limit 3`
2. Pun v1 baseline: `python evals/visualize_parent_runtime.py --label v1-baseline`

**Top_k odgovor:**
- `search_products` tool ima `top_k` default=5, max=10 (`app/tools.py:114–118`).
- Znači jedan tool poziv vrati maksimum 10 proizvoda.
- Ako Claude napravi više search poziva u jednom turn-u (npr. 3 iteracije), gornja granica je ~30.
- Nikada svih 638 iz PC periferija subtree — agent paradigma je "top-K + LLM curated".
- Ako se želi "list all" tipa endpoint, treba separate route mimo agent-a.

**Sljedeće faze (otvoreno):**
- Dashboard widget koji prikazuje koja je kategorija proslijeđena u trenutnom razgovoru ("danas je Claude za upit X poslao cat 277") — bolji uvid u runtime, da prestane da bude crna kutija. Već postoji `tool_calls` u ChatResponse i `_persist_trace` ide u bazu kroz dashboard — proširenje vidljivosti je u dashboard-u, ne API-ju.
- Strukturirani JSON output iz LLM-a za neke kategorije (već u planu za prompt modifikacije).

### Debug runbook — sve na jednom mjestu

User je tražio runbook po istom konceptu kao server services runbook — sve komande za debug na jedno mjesto.

**Napravljeno:** `bitlab-ai-asistent/RUNBOOK-debug.md` (~250 linija). Šest sekcija:

1. **Pokretanje servera** — uvicorn na port 7778 (eval default) ili 8000 (prod sim + vite proxy), vite dev za dashboard frontend, sibling playwright-router.
2. **Eval skripte** — tabela: koja skripta, dotiče li server, šta vidiš. Komande za svaku.
3. **Dashboard tabovi** — Requests, Request detail, Sessions, Stats, Errors, Overview, Compare. Bearer auth via `DASHBOARD_API_KEY`. Endpoint mapping `/api/dashboard/*`.
4. **Agent loop primer** — eksplicitan disambig između turn (user ↔ agent razmijena) i iteracije (agent ↔ tool unutar jednog turn-a). Default `max_tool_iterations=10`.
5. **Quick debug recipes** — pet konkretnih scenarija:
   - "Claude ne vraća očekivane proizvode" → koraci kroz runtime visualizer.
   - "Rezultat se promijenio nakon update-a" → A/B sa labelima.
   - "Vidjeti tačno šta je Claude poslao" → Request detail tab.
   - "Server radi ali sporo" → ss + ps komande.
   - "Name → cat lookup promašio" → refresh `all-products.json` ili fuzzy match.
6. **Linkovi** — na ostale runbook-e (`deploy/RUNBOOK-services.md`, `deploy/RUNBOOK-prod.md`, eval docstringovi).

Karakter: kompaktan i copy-paste prijateljski, svaka komanda u zasebnom code blocku.

---

## Status sesije

Sesija je trajala kroz nekoliko tematskih cjelina:
1. Početni topic — kako čitati `parent-expansion-*.html` (vrijednosti, banner, leaderboard, tree).
2. Branch realnost — fix je samo na `claude/analyze-category-hierarchy-dIVqm`, ne na staging/main.
3. Akutni incident — staging.aiasistent.bitlab.rs 502 zbog ručno stopiranih servisa, recovery preko cmd.sh.
4. Novi server services runbook (`deploy/RUNBOOK-services.md`).
5. Paradoks "PC periferija vraća rezultate iako fix nije primijenjen" — objašnjeno kroz hibridni search, smart LLM routing, soft boost.
6. Plan i implementacija runtime visualizer-a (`evals/visualize_parent_runtime.py`) + query set (`evals/parent_eval_set.json`).
7. Novi debug runbook (`bitlab-ai-asistent/RUNBOOK-debug.md`).

**Otvorena pitanja za sljedeću sesiju:**
- Pokretanje v1-baseline run-a — empirijska potvrda da `EXACT_PARENT` routing nije čest u praksi.
- Dashboard widget za routing vidljivost u realnom razgovoru (mimo eval skripti).
- Strukturirani JSON output iz LLM-a za određene kategorije.
- Merge `claude/analyze-category-hierarchy-dIVqm` → staging (kad bude vrijeme za parent fix u produkciji).

---

## Sesija 2 — 2026-05-21 (hard testing parent kategorija)

Voice sesija, BCS, ~6 sati. Cilj: pokrenuti `visualize_parent_runtime.py` na pravim podacima i analizirati šta sistem stvarno radi za parent kategorijske upite. Sesija je počela kao smoke test sa jednim upitom; otvorila nekoliko slojeva problema koji su sve do reda popravljeni.

### Otkrića o ponašanju sistema

**RAG je padao silent.** Početni smoke run je pokazao FAIL sa Sonnet/low/pwr za upit "Mobiteli". Tool output u dashboard bazi: *"Pretraga trenutno vraća prazan rezultat..."* — Claude je vidio tu poruku i halucinarao 6 izmišljenih Samsung Galaxy modela sa 256GB konfiguracijama koje ne postoje u našoj bazi (DB ima samo 128GB). Skripta je ispravno označila FAIL jer URL hash lookup nije našao ništa.

**Pravi uzrok**: `app/tools.py:dispatch` je imao **generičan `except Exception`** koji je gušio SVAKU grešku RAG-a i prevodio je u tu istu poruku. Tj. RAG zapravo NIJE vraćao prazno legitimno — bacao je exception koji se progutaje. Mehanizam je opasniji od greške jer Claude vidi "prazno" → halucinira → korisnik dobija listu izmišljenih proizvoda koji izgledaju realistično.

**Stvarni exception**: `NotImplementedError: Cannot copy out of meta tensor; no data!` iz `app/rag.py:282` (`SentenceTransformer(settings.embed_model, device="cpu")`). Stari komentar u kodu je objašnjavao zašto je `device="cpu"` ranije bio FIX za torch 2.x; sa torch 2.11 (silent upgraded preko `pip install -e .` 1. maja kroz nepin-ovan constraint `>=2.4,<3.0`) postao je BUG — sentence-transformers interno radi `self.to(device)` na meta tensor što nije podržano.

**PWR/Claude CLI tool flakiness**: paralelno otkriven od drugog Claude-a u playwright-router sesiji. Haiku 4.5 ponekad ignoriše bitlab-ov tekstualni protokol `⟦tool_use⟧{...}⟦/tool_use⟧` i pokušava native Claude Code tool call. Token budget potroši unutar tog envelope-a; result polje ostaje prazno; adapter baca grešku. Pattern u 200 zahtjeva: ~23% failure rate, "ok ok error ok ok error" — flaky ali ne random.

**Routing leaf vs parent**: za upit "Mobiteli" Claude konzistentno proslijedi `category_id="175"` (leaf "Mobilni telefoni", 167 proizvoda) umjesto `category_id="151"` (parent "Mobiteli", subtree 1575 proizvoda). Parent_id expansion fix radi dobro KAD Claude pošalje parent ID — ali tu šansu ne koristi. Hipoteza: tool description i sistem prompt sugerišu Claude-u "tačnu" leaf kategoriju umjesto parent-a.

**Output tokens fundamental limit**: 1575 proizvoda u markdown format-u sa slikama i linkovima je ~200-250K output tokena. Anthropic API hard cap je 64K (sa beta header-om do 128K). Preko PWR/Claude.ai web sesije, efektivni limit je još manji (~8-12K), jer Claude.ai web UI ima vlastite limite generisanja. Tj. "vrati svih 1575 u jednom chat odgovoru" je tehnički nemoguće sa trenutnom arhitekturom — za list-all treba zaobići agent (separate `/api/products` endpoint koji ne ide kroz Claude).

**`--reload` race condition**: `app/main.py` `lifespan` task se ne ponavlja pri uvicorn `--reload`-u, samo pri initial startup-u. Globalne varijable iz lifespan-a (`_rag_ready`, `_rag_error`) ostaju u stale stanju nakon code reload-a. Sa `--reload` izgleda kao da fix ne radi — ali samo treba pun-restart procesa.

### Šta je popravljeno

**1. `evals/visualize_parent_runtime.py` — UI i logika**:
- Mapiranje proizvoda na kategoriju ide preko URL hash-a (`urlhash` ili G-kod prefix iz `urlhash`), pa name fallback. URL je stabilan jer Claude ga doslovno kopira iz tool result-a; ime je nestabilno (skraćuje, izbacuje zareze, gubi model-kod).
- `subtree_total` sad pokazuje broj proizvoda u expected porodici (npr. Mobiteli 1575), ne broj kategorija (4). Prošli prikaz `in=2/4` je bio confusing.
- Prevod UI-a na BCS: `PASS`/`WARN`/`FAIL` → `dobar`/`upozorenje`/`promaši`; `EXACT_PARENT`/`DESCENDANT`/`NULL`/`OUT` → `baš parent`/`podkategorija`/`bez filtera`/`promašena`; `In subtree` → `Pogodaka`; verdict banner i stats kartice prevedeni.
- Model badge gore desno: `Sonnet 4.6 · low · via pwr` (auto-skraćeno iz pun model ID).
- Tabela kolone: `Rutovano na (kategorija)` sa imenom u zagradi (`175 (Mobilni telefoni)`); kompaktnijim brojkama sa `(proizvoda)` u sivom; sve numeričke kolone left-aligned umjesto right.
- Per-upit summary: `Mobiteli — dobar: 5 pogodaka od 5 vraćenih proizvoda (porodica Mobiteli ima 1575 proizvoda)`.
- Debug etikete za matching: "prepoznat preko URL adrese", "prepoznat po imenu" itd. umjesto "matchovan po urlhash".

**2. `/healthz` endpoint — readiness semantika**:
- Vraća stvarni `chat_model`/`chat_model_effort`/`llm_backend` umjesto Anthropic default-a (poštuje `LLM_BACKEND=pwr`).
- Dodato `rag_ready: bool` + `rag_error: str | None`.
- HTTP 503 dok `rag_ready=false`; 200 inače. Load balanceri / monitoring vide instancu kao not-ready dok RAG warmup nije završio.

**3. Defensive depth za sistemske greške**:
- Nova klasa `ToolValidationError` u `app/tools.py` za expected business case-ove.
- `dispatch()` hvata SAMO `ToolValidationError`; sve ostalo propagira (fail-fast, industrijski standard).
- Novi `_system_exception_handler` u `app/main.py` catch-all za nesvjetlim greškama → HTTP 503 sa structured payload `{"error":"service_unavailable","reply":"Imamo tehnički problem sa katalogom..."}`. Pun traceback u uvicorn stderr.
- Widget već čita `data.reply` (postojeći pattern za Anthropic exception handler-e), prikazuje kao bot poruku.

**4. Smoke test pri startup-u**:
- `_warmup_rag_sync()` u `app/main.py` nakon `preload_model()` pokrene `idx.search("test", top_k=1)`. Ako uspije, `_rag_ready=True`; ako pukne, `_rag_error="ExceptionType: poruka"`.
- Hvata regression sa silent dep upgrade-ovima prije nego što stigne prvi korisnik.

**5. Pin verzija u `pyproject.toml`**:
- `torch==2.11.0` (pinned).
- `sentence-transformers==3.4.1` (pinned).
- Komentar koji eksplicitno opisuje prošli incident, da niko ne otvori opseg ponovo.

**6. ENV varijabla `SEARCH_TOP_K_OVERRIDE`** (out-of-band override za eval):
- Polje u `config.py` sa upozorenjem "NIKAD u produkciji".
- `handle_search_products` ignoriše `top_k` koji Claude šalje kad je ENV setovan.
- Schema vraćena na originalno (max 10, default 5) jer in-prompt default nikad ne radi — Claude UVIJEK eksplicitno pošalje `top_k` pa schema default nije korišten.
- Dokumentovano u `.env` + `.env.example` zakomentarisano.

**7. Sistem prompt: render sve proizvode**:
- Dodat novi blok *"RENDERUJ SVE PROIZVODE IZ TOOL RESULT-A"* u `app/system_prompts.py` koji eksplicitno kaže da korisnik mora vidjeti svih N, bez curated.
- Prva verzija imala scaffold "ako > 50, predloži suženje nakon prvih 20" što je korisnik odbio kao samostalno skretanje — finalna verzija je jasna i bez scaffold-a.

**8. Timeout cleanup za hard testing** (6 mjesta, sva sa "VRATITI prije produkcije" komentarima):

| Fajl | Trenutno | Vratiti na |
|---|---|---|
| `app/config.py:max_output_tokens` | 64000 | 1024 |
| `.env:SEARCH_TOP_K_OVERRIDE` | 5287 | komentarisano |
| `evals/visualize_parent_runtime.py:DEFAULT_TIMEOUT_S` | 900 | 180 |
| `app/agent.py:_get_pwr_client timeout` | 1800 | 180 |
| `playwright-router/.../claude_cli_adapter.py:DEFAULT_TIMEOUT_S` | 1800 | 600 |
| `playwright-router/.../claude_adapter.py:SEND_TIMEOUT_S` + `STREAM_OVERALL_TIMEOUT_S` | 1800 + 1800 | 180 + 240 |

**9. Dvije nove kartice u `STATUS.md` Doing**:
- `id:rtct` — Routing: Claude bira leaf cat 175 umjesto parent cat 151. DoD: ≥80% upita iz `parent_eval_set.json` ima `EXACT_PARENT` ili pametan `DESCENDANT` routing.
- `id:pwhk` — PWR/Claude CLI tool call flakiness na Haiku adapteru. Preporuka: kombinacija few-shot u sistem prompt-u + jednokratni retry u adapteru.

### Feedback memorije ažurirane

- `feedback_natural_language_voice.md` — voice (say.sh) bez tehničkih kratica (WARN/subtree/DESCENDANT); prevodi na ljudski ("upozorenje", "porodica", "smart rutovao u podkategoriju"). Razlog: korisnik prati glasom dok radi druge stvari, ne vidi UI.
- `feedback_test_case_invariant.md` — kad podešavamo sistem, eval/test case NE diramo. Mijenja se samo varijabla pod ispitivanjem. Razlog: bez fiksnog test case-a nema A/B compare. Ja sam u sesiji zamutio dva nezavisna lijevera (schema top_k + eval query) i korisnik me ispravio.

### Status na kraju sesije

Server radi, healthz vraća 200 sa `rag_ready: true`. Eval skripta i dalje "ne vraća 1575" jer:
- (a) Sa Claude/PWR ne može output > ~64K (fundamental token limit).
- (b) Claude rutira na cat 175 (167 proizvoda) ne cat 151 (1575) — to je routing problem otvoren u `STATUS.md id:rtct`.

Dobio se uvid u **kakve grane problema postoje** i **gdje se može a gdje ne može popraviti**:
- Popravljiv u kodu: silent exception, lookup po imenu, healthz endpoint, timeout-i.
- Otvoreno za sledeće: routing leaf vs parent (treba prompt engineering ili tool description tuning), PWR Haiku flakiness (treba adapter ili few-shot).
- Arhitekturno limit: "vrati svih 1575 u chat-u" — fundamentalno preko output token limita. Treba zasebni endpoint mimo agent loop-a ako se to baš želi.

Nije commit-ovano. Sve izmjene su u working tree-u; korisnik je rekao da se sve može vratiti za produkciju (timeout-i, max_output_tokens, ENV, sistem prompt blok). Pin verzija + healthz readiness + smoke test + fail-fast handler + URL hash lookup su trajne arhitekturalne popravke koje ostaju kad se hard-testing override-i vrate.






