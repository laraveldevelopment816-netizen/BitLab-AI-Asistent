# Inventar repozitorijuma — bitlab-ai-asistent

Inventar fajlova klasifikovan po statusu, grupisan po logičkim komponentama.

- **Generisano:** 2026-06-07 · grana `feat/ralph-categories-eval`
- **Obuhvat:** svih 360 git-praćenih fajlova. 254 fajla u `bck/` su sažeti u jedan red (izuzetak za arhivu); ostalih 106 fajlova je klasifikovano pojedinačno.
- **Metod:** 13 Sonnet scan agenata pročitalo je i klasifikovalo fajlove po komponentama (svaki je grep-ovao repo da potvrdi reference prije bilo kakve DEAD oznake), pa su rezultati provjereni i sintetizovani. Gdje je provjera oborila sirovu ocjenu agenta, koristi se korigovani status, a razlog je naveden na dnu.
- **Kontekst:** ovaj repo je usred *TDD zero-base reseta* — sav stari full-stack kod je namjerno premješten u `bck/`, a minimalno jezgro se ponovo gradi, vođeno padajućim eval unosima. Trenutna Now inicijativa je popravka regresije categories-routing eval-a (iter17 pao sa 84.4% → 79.2%) nazad do ≥95% acceptance forsiranjem tool poziva.

## Legenda

- **ACTIVE** — dio trenutnog radnog sistema: importovan/pokretan od strane žive aplikacije, eval frameworka, trenutnih testova, Ralph petlje, trenutnih skripti/konfiguracije/CI-ja, ili planskih dokumenata koji odražavaju trenutni rad.
- **DRAFT** — rad u toku ili rezervisano mjesto za još neizgrađen posao (npr. specifikacije budućih faza).
- **ARCHIVED** — namjerno zadržano kao referenca, ali nije dio aktivnog sistema (`bck/` stablo, zadržani artefakti runova, namjenski materijali).
- **DEAD** — siroče, prevaziđeno ili sigurno za brisanje; nije referencirano ni od čega aktivnog.

## Sažetak

| Status | Broj |
|---|---|
| ACTIVE | 96 |
| ARCHIVED | 8 |
| DRAFT | 2 |
| DEAD | 1 |
| **Ukupno** | **107** (106 fajlova + `bck/` kao jedan red) |

Aktivna baza koda je zdrava i usko fokusirana: gotovo sve što je praćeno nosi teret trenutnog categories-eval rada. Postoji tačno jedan fajl za uklanjanje (`evals/sets/.gitkeep`), dvije DRAFT specifikacije za buduće faze i šačica namjerno zadržanih referentnih/materijalnih fajlova.

---

## 1. Backend aplikacija — `app/`, `data/`

Deployabilno jezgro nakon reseta: minimalni FastAPI servis čiji jedini stvarni endpoint, `/api/chat`, pokreće forsiranu tool-use dispatch petlju preko dva zamjenjiva LLM backenda (PWR podrazumijevano, Anthropic kao fallback) i rutira svaki upit kroz katalog alate definisane jednom u `tools.py`. `config.py` centralizuje podešavanja (model, temperatura, `category_id` enum prekidač, izbor backenda), a `data/categories_new.json` je živa taksonomija koja stoji iza tool stubova i svakog eval-a. Svih šest fajlova je ACTIVE i nosi teret — ovo je površina koju trenutna routing inicijativa šteluje.

| Fajl | Status | Šta radi |
|---|---|---|
| `app/__init__.py` | ACTIVE | Označava `app` direktorijum kao Python paket i izlaže verziju; importovan tranzitivno od strane eval runnera, testova i skripti. |
| `app/agent.py` | ACTIVE | Implementira `run_agent`, forsiranu tool-use LLM dispatch petlju (Anthropic + PWR backendi) koju `main.py` poziva pri svakom `/api/chat` zahtjevu i koju koristi eval framework. |
| `app/config.py` | ACTIVE | Definiše `Settings` pydantic model (API ključevi, model, temperatura, `category_id_enum` zastavica, izbor backenda) koji `agent.py` i `tools.py` importuju pri pokretanju. |
| `app/main.py` | ACTIVE | Živi FastAPI ulaz: montira `/public` statičke fajlove, registruje openai+anthropic rate-limit→429 handlere i izlaže `/`, `/healthz` i `/api/chat`. |
| `app/tools.py` | ACTIVE | Jedinstveni izvor istine za tool sheme (`category_overview`, `search_products`, `respond_to_user`) u Anthropic i OpenAI obliku, plus `dispatch` handler oslonjen na `data/categories_new.json`. |
| `data/categories_new.json` | ACTIVE | Živa taksonomija kategorija učitana pri pokretanju u `tools.py` za izgradnju parent/leaf ID enuma i child-category lookup-a koji se koriste u svakom eval-u i integracionom testu. |

## 2. Browser frontend — `public/`

Klijentska strana servirana direktno sa FastAPI statičkog mount-a: `widget.html` je demo host stranica vraćena na `/`, `widget.js` je ugradivi v3 chat widget (sa voice overlay-em isključenim preko `VOICE_ENABLED=false`), a `voice.html` je samostalna voice stranica na koju widget linkuje kao fallback. `favicon.ico` je u aktivnoj upotrebi; preostali materijali — pitch brief, dva pitch PDF-a, PPTX i `bitlabLogo.png` — su namjerno zadržani marketinški materijali bez referenci u kodu, klasifikovani kao ARCHIVED umjesto obrisani.

| Fajl | Status | Šta radi |
|---|---|---|
| `public/widget.html` | ACTIVE | Demo webshop host stranica koju `main.py` servira na `/`, ugrađuje `widget.js` kao živi chat interfejs. |
| `public/widget.js` | ACTIVE | Ugradivi chat widget v3 (markdown + product card-ovi, praćenje sesije, voice overlay) učitan preko script tag-a u `widget.html`; in-widget voice overlay je isključen preko `VOICE_ENABLED=false`. |
| `public/voice.html` | ACTIVE | Samostalna voice-only stranica asistenta (animirani orb, VAD petlja, STT/chat/TTS) servirana na `/public/voice.html` i linkovana iz `widget.js` kao voice fallback — trenutna ulazna tačka za voice dok je ugrađeni overlay isključen. |
| `public/assets/favicon.ico` | ACTIVE | Ikona browser taba referencirana iz `widget.html` i `voice.html`, servirana preko statičkog mount-a. |
| `public/assets/PITCH-BRIEF.md` | ARCHIVED | Kompletan brief za dizajnera pitch deck-a (brend, diferencijatori, demo flow, ROI, spec za 12 slajdova); namjerno zadržan marketinški materijal bez referenci u kodu. |
| `public/assets/img/bitlabLogo.png` | ARCHIVED | BitLab brend logo zadržan kao materijal; nije referenciran ni iz jednog serviranog HTML/JS-a (`favicon.ico` je onaj koji je stvarno u upotrebi). |
| `public/assets/BitLab AI Asistent — Engineering Pitch v2.pdf` | ARCHIVED | PDF engineering pitch deck-a zadržan kao marketinški materijal, nereferenciran iz koda koji se pokreće. |
| `public/assets/BitLab AI Asistent.pdf` | ARCHIVED | Originalni PDF pitch deck-a zadržan kao marketinški materijal, nereferenciran iz koda koji se pokreće. |
| `public/assets/BitLab_AI_Asistent.pptx` | ARCHIVED | Editabilni PowerPoint pitch deck zadržan kao marketinški materijal, nereferenciran iz koda koji se pokreće. |

## 3. Eval framework — `evals/framework/`

Deterministički, parser-baziran evaluacioni engine koji je kičma cijelog TDD pristupa: jedan `runner.py` povezuje JSONL `loader`, stratifikovani `sampler`, SHA-256 verdict `cache`, `budget` tracker sa kliznim prozorom za PWR, HTTP `client`, čisti `judge` i HTML/JSONL `reporter`, sve tipizovano prema jednom zajedničkom `types.py` ugovoru. Svaki fajl je ACTIVE; framework podržava checkpoint/resume i pauziranje bezbjedno na rate-limit, tako da dugi runovi od 250 slučajeva prežive PWR session resete.

| Fajl | Status | Šta radi |
|---|---|---|
| `evals/__init__.py` | ACTIVE | Package init za `evals` namespace. |
| `evals/framework/__init__.py` | ACTIVE | Package init koji dokumentuje jedinstvenu shemu frameworka i pozivanje runnera. |
| `evals/framework/budget.py` | ACTIVE | Prati PWR API pozive u kliznom prozoru od 5 sati i signalizira runneru da pauzira prije iscrpljivanja budžeta. |
| `evals/framework/cache.py` | ACTIVE | Disk-based SHA-256 verdict keš koji preskače ponovljene PWR pozive kad su prompt i alati nepromijenjeni. |
| `evals/framework/client.py` | ACTIVE | HTTP klijent koji POST-uje eval upite na `/api/chat` i diže `RateLimitDetected` na HTTP 429. |
| `evals/framework/errors.py` | ACTIVE | Definiše `RateLimitDetected`, prilagođeni izuzetak koji se propagira od klijenta do runnera za checkpoint-safe rukovanje. |
| `evals/framework/judge.py` | ACTIVE | Čisti deterministički sudija koji proizvodi routing/result/overall verdikte iz eval unosa i stvarnih tool poziva. |
| `evals/framework/loader.py` | ACTIVE | Učitava i validira JSONL eval suite-ove, namećući obavezna polja i postavljajući podrazumijevane vrijednosti za opciona. |
| `evals/framework/reporter.py` | ACTIVE | Piše per-entry JSONL append logove, vremenski označene HTML dashboard-e i terminalske sažetke za svaki run. |
| `evals/framework/runner.py` | ACTIVE | Orkestrira izvršavanje cijelog suite-a sa kešom, budget gating-om, checkpoint/resume i sampling modovima. |
| `evals/framework/sampler.py` | ACTIVE | Proizvodi reproducibilan stratifikovan uzorak od ~30 unosa da smanji PWR trošak po Ralph iteraciji. |
| `evals/framework/types.py` | ACTIVE | Definiše kanonske TypedDict-ove (EvalEntry, EvalVerdict, ToolCall, ExpectClause) dijeljene kroz framework. |

## 4. Eval skupovi podataka i artefakti runova — `evals/sets/`, `evals/runs/`

Korpusi protiv kojih framework radi: kanonski auto-generisani `categories.jsonl` master suite plus četiri fokusirana podskupa (težak dev uzorak, acceptance-fail set, leaf-tune set, ručno održavani negativci) koji sprovode disciplinu „razvoj na teškom uzorku, pun eval jednom" iz `STATUS.md`. Stabilni `categories-acpt.jsonl` log je ACTIVE, vremenski označeni HTML izvještaj je zadržani ARCHIVED artefakt, a zaostali `.gitkeep` je sada suvišan jer je direktorijum popunjen.

| Fajl | Status | Šta radi |
|---|---|---|
| `evals/sets/categories.jsonl` | ACTIVE | Auto-generisan primarni eval suite (254 unosa) učitan kao kanonski „categories" suite za acceptance i regresione runove. |
| `evals/sets/categories_acpt_fails.jsonl` | ACTIVE | Auto-generisan težak podskup (15 acceptance padova + 8 negativaca) iz posljednjeg punog runa, korišten kao jeftin regresioni gate. |
| `evals/sets/categories_dev.jsonl` | ACTIVE | Auto-generisan težak dev uzorak (29 iter8→iter17 regresija + 8 negativaca) za brzu/jeftinu iteraciju prompta. |
| `evals/sets/categories_leaf_tune.jsonl` | ACTIVE | Ručno kuriran tune set (15 leaf-routing padova + 6 halucinacijskih false-positive-a); validacioni set za trenutnu leaf-routing popravku. |
| `evals/sets/categories_manual.jsonl` | ACTIVE | Ručno održavan negativni set (`expect.tool=null`) koji hrani dev/acpt generatore slučajevima van kataloga i dvosmislenim slučajevima. |
| `evals/sets/.gitkeep` | DEAD | Suvišno rezervisano mjesto direktorijuma — folder sada sadrži stvarne eval setove, pa nema svrhe. |
| `evals/runs/categories-acpt.jsonl` | ACTIVE | Stabilan (bez vremenske oznake) JSONL log koji `run_acceptance.sh` i runner dopisuju kao kanonski zapis rezultata acceptance runa od 250 slučajeva. |
| `evals/runs/categories-acpt-20260607-130937.html` | ARCHIVED | Vremenski označen HTML izvještaj za posljednji pun run od 250 slučajeva (commit `075affc`); zadržani istorijski artefakt, nije referenciran ni iz jedne aktivne skripte. |

## 5. Generatori eval setova i smoke alati — `scripts/`

Regenerabilni pipeline koji proizvodi te skupove podataka iz izvora istine: `gen_categories_eval.py` izvodi kanonski suite iz `data/categories_new.json` po `specs/categories.md`, dok `gen_acpt_fails.py` i `gen_dev_sample.py` izdvajaju teške podskupove iz verdikata ranijih runova, `run_acceptance.sh` vodi grupisani (batched) acceptance gate od 250 slučajeva, a `smoke.py` je alat za vizuelnu provjeru (bez ocjene) za štelovanje prompta. Svi ACTIVE i direktno vezani za trenutnu inicijativu.

| Fajl | Status | Šta radi |
|---|---|---|
| `scripts/__init__.py` | ACTIVE | Čini `scripts/` paketom da generatori rade kao `python -m scripts.*` i da se importuju u unit testove. |
| `scripts/gen_categories_eval.py` | ACTIVE | Auto-generiše kanonski `categories.jsonl` iz `data/categories_new.json` po `specs/categories.md`; unit-testiran. |
| `scripts/gen_acpt_fails.py` | ACTIVE | Generiše `categories_acpt_fails.jsonl` iz FAIL verdikata posljednjeg acceptance runa plus negativci, kao jeftin gate. |
| `scripts/gen_dev_sample.py` | ACTIVE | Generiše `categories_dev.jsonl` za brzu povratnu informaciju iz iter8-PASS/iter17-FAIL regresija plus negativci. |
| `scripts/run_acceptance.sh` | ACTIVE | Pokreće pun acceptance suite od 250 unosa u grupama koje nastavljaju kroz PWR session resete; acceptance gate naveden u `STATUS.md`. |
| `scripts/smoke.py` | ACTIVE | Ručni alat za vizuelnu provjeru (bez ocjene) koji poziva `run_agent` na reprezentativnim upitima radi pregleda routinga tokom štelovanja prompta. |

## 6. Ralph autonomna TDD petlja — `ralph/`

Samovozeća skela (harness) koja pokreće build ciklus bez nadzora: `ralph.sh` šalje `PROMPT_build.md` Claude CLI-ju u svakoj iteraciji, poštujući STOP/PAUSE markere i pozivajući `wait_pause.py`/`estimate_reset.py` za odustajanje (back off) oko PWR prozora od 5 sati, sa `IMPLEMENTATION_PLAN.md` kao živom tablom zadataka, `AGENTS.md` kao operativnim priručnikom i `status.sh` kao dashboard-om. Svi ACTIVE — iako akcioni plan ističe otvoreno pitanje (`evfx`) da li je autonomna petlja još potrebna sad kad je tool calling mehanički forsiran.

| Fajl | Status | Šta radi |
|---|---|---|
| `ralph/ralph.sh` | ACTIVE | Glavni vozač autonomne TDD petlje koji šalje `PROMPT_build.md` Claude CLI-ju, rukuje STOP/PAUSE markerima i poziva pause/reset helpere. |
| `ralph/ralph-plan.sh` | ACTIVE | Jednolinijska omotačica koja pokreće jednu plan-mode iteraciju sa `PROMPT_plan.md`. |
| `ralph/PROMPT_build.md` | ACTIVE | Build-mode prompt koji vodi Claude-a kroz orijentaciju → implementaciju → backpressure → commit u svakoj iteraciji. |
| `ralph/PROMPT_plan.md` | ACTIVE | Plan-mode prompt koji nalaže gap analizu i ažuriranja `IMPLEMENTATION_PLAN.md` bez diranja app koda. |
| `ralph/AGENTS.md` | ACTIVE | Operativni priručnik koji svaka iteracija prvo pročita: repo komande, backpressure pravila, LLM dispatch imperative, pravila petlje. |
| `ralph/IMPLEMENTATION_PLAN.md` | ACTIVE | Živa Now/Next/Done tabla koju Ralph čita da odabere vrh zadatka i ažurira nakon svake iteracije. |
| `ralph/status.sh` | ACTIVE | Dashboard koji izvještava o stanju Ralph procesa, posljednjim redovima loga, skorašnjim commit-ima, broju zadataka u planu i posljednjem eval PASS rate-u. |
| `ralph/wait_pause.py` | ACTIVE | Helper koji poll-uje PAUSE marker do epohe auto-nastavka (ili kooperativnog `rm`), signalizirajući nastavak naspram izlaza. |
| `ralph/estimate_reset.py` | ACTIVE | Helper pozvan na exit kodu 3 da procijeni epohu reseta PWR rate-limit prozora; unit- i integraciono-testiran. |
| `ralph/logs/.gitkeep` | ACTIVE | Drži gitignored `ralph/logs/` direktorijum prisutnim da `ralph.sh` može tu pisati vremenski označene logove. |

## 7. Test suite — `tests/`

Kompletna pytest piramida (`unit`, `integration`, `e2e`, `regression`) sa `conftest.py` koji mock-uje oba LLM klijenta tako da nijedan test nikad ne pogađa stvarni API (tvrdo budžetsko ograničenje). Pokrivenost naginje — prikladno — ka eval frameworku i Ralph helperima; svaki fajl je ACTIVE, sa e2e i regression slojevima koji su trenutno tanka rezervisana mjesta koja rastu kako eval unosi počnu da prolaze.

| Fajl | Status | Šta radi |
|---|---|---|
| `tests/conftest.py` | ACTIVE | Dijeljene fixture (mock LLM klijenti, test klijent, forsiranje backenda) koje sprečavaju stvarne LLM pozive kroz cijeli suite. |
| `tests/__init__.py` | ACTIVE | Package marker koji omogućava pytest otkrivanje `tests/` paketa. |
| `tests/unit/__init__.py` | ACTIVE | Package marker koji omogućava pytest otkrivanje `unit` sloja. |
| `tests/integration/__init__.py` | ACTIVE | Package marker koji omogućava pytest otkrivanje `integration` sloja. |
| `tests/e2e/__init__.py` | ACTIVE | Package marker koji omogućava pytest otkrivanje `e2e` sloja. |
| `tests/regression/__init__.py` | ACTIVE | Package marker koji omogućava pytest otkrivanje `regression` sloja. |
| `tests/unit/test_eval_budget.py` | ACTIVE | Unit testovi za budget tracker (brojač sa kliznim prozorom i prag za pauzu). |
| `tests/unit/test_eval_cache.py` | ACTIVE | Unit testovi za verdict keš i stratifikovani sampler. |
| `tests/unit/test_eval_client.py` | ACTIVE | Unit testovi da HTTP 429 → `RateLimitDetected`, dok se ostale greške propagiraju. |
| `tests/unit/test_eval_errors.py` | ACTIVE | Unit testovi da je `RateLimitDetected` ispravan Exception koji čuva svoju poruku. |
| `tests/unit/test_eval_framework.py` | ACTIVE | Unit testovi za čiste funkcije judge/loader/reporter. |
| `tests/unit/test_gen_categories_eval.py` | ACTIVE | Unit testovi za categories generator (pravila routinga, shema, determinističan izlaz). |
| `tests/unit/test_ralph_pause.py` | ACTIVE | Unit testovi za `wait_pause.py` i `estimate_reset.py`. |
| `tests/unit/test_ralph_prompt.py` | ACTIVE | Guard testovi da Ralph prompt/AGENTS fajlovi sadrže obavezne guardrail sekcije. |
| `tests/unit/test_smoke.py` | ACTIVE | Potvrđuje da su `app` paket i njegovi dual-backend atributi importabilni. |
| `tests/unit/test_system_prompt.py` | ACTIVE | Provjerava da je `SYSTEM_PROMPT_V1` definisan, imenuje oba alata i stiže do oba runnera. |
| `tests/integration/test_eval_runner_budget.py` | ACTIVE | Integracioni testovi runner↔budget gating-a i invarijante keš-pogodak-bez-budžeta. |
| `tests/integration/test_eval_runner_cache.py` | ACTIVE | Integracioni testovi runner keša (pogodak/promašaj, limit, fail-fast, sample mod, invalidacija). |
| `tests/integration/test_eval_runner_resume.py` | ACTIVE | Integracioni testovi checkpoint/resume, detekcije neslaganja moda i auto-detekcije početnog indeksa. |
| `tests/integration/test_main_rate_limit.py` | ACTIVE | Integracioni testovi da FastAPI mapira `RateLimitError` oba SDK-a u HTTP 429. |
| `tests/integration/test_runner_writes_pause_marker.py` | ACTIVE | Integracioni testovi da se validan PAUSE marker piše na budget/rate-limit izlaze, a izostaje na čistom završetku. |
| `tests/integration/test_smoke.py` | ACTIVE | Integracioni smoke za `/healthz` i `/api/chat` sa oba backenda mock-ovana. |
| `tests/integration/test_status_script.py` | ACTIVE | Pokreće `ralph/status.sh` i tvrdi exit 0 plus sve dashboard sekcije. |
| `tests/integration/test_tool_dispatch.py` | ACTIVE | Integracioni testovi tool dispatch-a kroz oba backenda i oblika koje handler vraća. |
| `tests/e2e/test_smoke.py` | ACTIVE | E2e smoke da je Playwright importabilan, preskače kad browser toolchain nije prisutan. |
| `tests/regression/test_smoke.py` | ACTIVE | Rezervisano mjesto regresionog sloja koje raste kako eval unosi prolaze. |

## 8. Specifikacije — `specs/`

Ugovori faza: `categories.md` je ACTIVE specifikacija Faze 1 koja vodi tool sheme, generisanje eval-a i acceptance kriterijume, dok su `products.md` (Faza 2 RAG) i `cross-reference.md` (Faza 3 multi-tool) eksplicitna DRAFT rezervisana mjesta za neizgrađene buduće faze.

| Fajl | Status | Šta radi |
|---|---|---|
| `specs/categories.md` | ACTIVE | Specifikacija categories-routinga za Fazu 1 (tool sheme, pravila generisanja eval-a, ≥95% acceptance) koja aktivno vodi `tools.py`, testove, generator i Ralph. |
| `specs/products.md` | DRAFT | Rezervisana specifikacija Faze 2 za RAG pretragu proizvoda, eksplicitno još neimplementirana i čeka acceptance Faze 1. |
| `specs/cross-reference.md` | DRAFT | Rezervisana specifikacija Faze 3 za multi-tool cross-reference upite (kategorija × cijena × brend), čeka Fazu 2. |

## 9. Dokumentacija, planiranje i status — root `*.md`, `docs/`

Dvonivovski model planiranja plus prateća analiza: `STATUS.md`/`STATUS-HUMAN.md` su taktički Kanban (mašinski + ljudski), `docs/plans/akcioni-plan.md` strateški Now/Next/Later, `PLAN.md` temeljna pravila TDD-reseta, a `RESTORE.md` recept za ponovnu izgradnju cijele aplikacije iz `bck/`. Uz to su post-mortemi i infra logovi (`EVAL_REGRESIJA_iter17.md`, `EVAL_OPTIMIZACIJA.md`, `docs/eval-infra-*`, `docs/PROMPT-BEST-PRACTICES.md`, `docs/work/...` session tabla) koji direktno informišu trenutnu popravku. Skoro svi ACTIVE; dva `repo-map*.md` kataloga su trenutni održavani snapshotovi (regenerisani danas), a `docs/fb-funnel-progress.md` je ARCHIVED pokazivač na nepovezan eksperiment u sibling repou.

| Fajl | Status | Šta radi |
|---|---|---|
| `STATUS.md` | ACTIVE | Formalni Kanban koji prati aktivne Doing/Todo zadatke za popravku categories routing eval-a, plus poznata ograničenja i pravila eval discipline. |
| `STATUS-HUMAN.md` | ACTIVE | Pratilac `STATUS.md` na prirodnom jeziku koji objašnjava regresiju i svaku karticu radi brze ljudske orijentacije. |
| `PLAN.md` | ACTIVE | Plan TDD zero-base reseta (temeljna pravila) na koji `STATUS.md` linkuje. |
| `README.md` | ACTIVE | Brzi vodič za programere: Ralph komande, pozivi eval runnera, grupisani acceptance runner od 250 slučajeva. |
| `RESTORE.md` | ACTIVE | Recept za oporavak cijele pre-reset aplikacije iz `bck/`; živa sigurnosna mreža tokom ponovne izgradnje. |
| `EVAL_REGRESIJA_iter17.md` | ACTIVE | Post-mortem iter17 regresije (84.4% → 79.2%) koji definiše baseline, korijenski uzrok i mapu oporavka koja vodi Now inicijativu. |
| `EVAL_OPTIMIZACIJA.md` | ACTIVE | Dizajn dokument sa pet strategija smanjenja PWR troška plus code review rate-limit-checkpoint-a sada implementiran u eval infri. |
| `CLAUDE.md` | ACTIVE | Projektna Claude Code konfiguracija: deployment URL-ovi + import dijeljenih bitlab-standards pravila, učitava se svake sesije. |
| `repo-map.md` | ACTIVE | Održavan katalog cijelog repoa sa opisima po fajlu (regenerisan 2026-06-07); trenutni snapshot dokumentacije, komplementaran ovom fajlu. |
| `repo-map-simplified.md` | ACTIVE | Održavan pojednostavljen katalog sa statusnim oznakama; trenutni ljudski-čitljiv snapshot dokumentacije. |
| `docs/plans/akcioni-plan.md` | ACTIVE | Strateški Now/Next/Later plan koji definiše Now inicijativu (categories eval do ≥95%) i okvirno postavlja Fazu 2/3. |
| `docs/PROMPT-BEST-PRACTICES.md` | ACTIVE | Istraživanje/preporuke o `tool_choice` + arhitekturi prompta koje informišu trenutnu popravku; referencirano u `STATUS.md`. |
| `docs/eval-infra-changelog.md` | ACTIVE | Hronološki after-action log eval-infra sesija (keš, sampler, resume, budget, PAUSE); referencirano u `README.md`. |
| `docs/eval-infra-review.md` | ACTIVE | Punch-list pregled eval infre iz Sesije 2 koji prati koje su popravke ušle i koje polish stavke ostaju. |
| `docs/work/2026-05-29-eval-acceptance/board.html` | ACTIVE | Živa session tabla za Now inicijativu koja prikazuje odluke, orijentaciju i sljedeće korake. |
| `docs/work/2026-05-29-eval-acceptance/nalaz-fail-set-enum-temp.md` | ACTIVE | Analiza enum+temperatura fail-set runa od 2026-06-05 koja identifikuje 7 preostalih padova i sljedeći korak. |
| `docs/fb-funnel-progress.md` | ARCHIVED | Navigacioni dnevnik zasebnog B2B akvizicijskog eksperimenta u sibling repoima (`ralph-fb-funnel`/`-prospector`); uspavan i van scope-a za categories-eval rad ovog repoa. |

## 10. Build konfiguracija i CI — `.github/`, root config

Toolchain i gate-ovi: `pyproject.toml` definiše zavisnosti i ruff/mypy/pytest konfiguraciju, `.pre-commit-config.yaml` ih nameće na svaki commit, `.gitattributes`/`.gitignore`/`.env.example` rješavaju higijenu i tajne, `scan.sh` proizvodi dump repoa za eksterne agente, a tri GitHub Actions workflow-a pokreću CI (ruff/mypy/pytest), Playwright e2e i noćni real-LLM eval. Svi ACTIVE.

| Fajl | Status | Šta radi |
|---|---|---|
| `pyproject.toml` | ACTIVE | Zavisnosti projekta, build konfiguracija i ruff/mypy/pytest podešavanja i test markeri za cijeli sistem. |
| `.pre-commit-config.yaml` | ACTIVE | Pre-commit hook-ovi (ruff format/lint, mypy, pytest unit) koji gate-uju svaki commit. |
| `.gitignore` | ACTIVE | Isključuje build artefakte, tajne, eval keševe, Ralph markere i generisane podatke. |
| `.gitattributes` | ACTIVE | Nameće LF završetke linija za tekst/shell fajlove radi izbjegavanja CRLF buke na WSL/Windows. |
| `.env.example` | ACTIVE | Šablon svih obaveznih/opcionih env varijabli (LLM backend, TTS/STT, webshop, eval override-i). |
| `scan.sh` | ACTIVE | Generiše jednofajlni `repo-scan.md` dump svih praćenih tekstualnih fajlova za eksterne agente. |
| `.github/workflows/ci.yml` | ACTIVE | Pokreće ruff, mypy i pytest (unit + integration) na push/PR ka tdd-zero-base i `feat/**` granama. |
| `.github/workflows/e2e.yml` | ACTIVE | Pokreće Playwright e2e testove na PR-ovima ka integracionoj grani. |
| `.github/workflows/eval-nightly.yml` | ACTIVE | Pokreće real-LLM categories eval noćno u 03:00 UTC i upload-uje artefakte. |

## 11. Arhiva prije reseta — `bck/`

| Folder | Status | Šta radi |
|---|---|---|
| `bck/` | ARCHIVED | Arhiva stare full-stack baze koda prije reseta (254 praćena fajla) — app kod, React dashboard, podaci, deploy konfiguracije, dokumentacija, evals, n8n workflow-i, skripte i testovi — zadržana kao referenca i obnovljiva preko `RESTORE.md`, ali nije importovana niti pokretana od strane bilo kog dijela aktivnog sistema. |

---

## Napomene

**Nepraćeni artefakti na disku** (nisu među 360 praćenih fajlova, pa nisu klasifikovani gore): `repo-scan.md` (~21 MB, generisan od `scan.sh`), `var/bitlab.db` (~1.7 MB SQLite, gitignored), nepraćeni `dashboard/` direktorijum i keševi alata (`.venv`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.idea`, `bitlab_ai_asistent.egg-info`). Svi su regenerisani ili lokalni i mogu se zanemariti za potrebe inventara.

**Procjene/odluke** (gdje je sirova ocjena agenta korigovana nakon provjere referenci):
- `public/voice.html` → **ACTIVE** (ne DEAD): linkovan iz `widget.js:1899` i serviran preko `/public` statičkog mount-a u `main.py`; brisanje bi pokvarilo voice fallback.
- pitch deck / brief / logo (`PITCH-BRIEF.md`, oba PDF-a, PPTX, `bitlabLogo.png`) → **ARCHIVED** (ne DEAD): namjerni marketinški materijali, ne siročad.
- `repo-map.md`, `repo-map-simplified.md` → **ACTIVE** (ne DRAFT): commit-ovani i regenerisani 2026-06-07, tj. održavana trenutna dokumentacija.
- `docs/fb-funnel-progress.md` → **ARCHIVED** (ne DEAD): cross-repo pokazivač na uspavan eksperiment u sibling repou, zadržan kao referenca.
- `evals/sets/.gitkeep` je jedini stvarno uklonjiv fajl — direktorijum koji je držao otvorenim sada je popunjen.
