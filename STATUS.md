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

## Todo

- [ ] P1 hotfix-evi (C2/C3/C4) — locks + Whisper preload + exception handlers <!-- id:p1fx -->
  C2: `threading.Lock` (double-checked) u 4 lazy-singleton helpera
  (`app/rag.py`, `app/agent.py`, `app/tools.py`, `app/main.py`). C3: Whisper
  preload kao background task u `lifespan` (sad lifespan preloaduje samo
  embedding, komentar laže). C4: centralni `@app.exception_handler` + handle
  za `anthropic.APIStatusError`/`APIConnectionError` na `/api/chat`,
  `/api/email`, `/api/tts`. Izvor: `docs/reviews/code-review.md` (Sesija 7.7).
- [ ] P2 fix-evi (C7/C8) + cold-start warm-up <!-- id:p2cs -->
  C7: `_HALLUCINATIONS` na module-scope `frozenset` (sad se alocira po
  `/api/stt` pozivu). C8: lazy API key validacija — `Settings()` se i dalje
  instancira na import time, što ruši testove/CI bez `.env`. Cold-start:
  explicit warm-up u `lifespan` task-u umjesto čistog background-a (prvi
  `/api/chat` sad čeka 30–50s).
- [ ] Strukturirani layout rezultata pretrage — AI vraća JSON, widget renderuje <!-- id:slay -->
  Trenutno chat AI sam generiše markdown layout za proizvode (slika + naziv +
  cijena + "Na lageru" link), i layout puca na 6-7 rezultata (dokumentovan
  slučaj u `docs/Otvorena pitanja sa Google Drive-a.md` — "Puca layout na
  laptopove ponovo, Koliko imate laptopova do 3000 eura"). Voice mode već
  renderuje product cards programski (vidi `docs/features/voice-mode.md`) —
  chat treba isti princip. Koraci:
  1. Definisati JSON shemu za `search_products` rezultate u response (može
     XML tag tipa `<products>…</products>` ili JSON block u envelopi).
  2. Ažurirati system prompt — AI vraća rezultate ISKLJUČIVO u toj schemi,
     bez inline markdown za proizvode (samo prose oko njih).
  3. `public/widget.js` chat path — parser za structured block + render kao
     product cards (re-use voice mode card komponentu ako moguće).
  4. Regresioni test (vez sa `tst1`/`evl1`): "AI vraća N proizvoda kao
     strukturirani output za 5/10/20 rezultata" + golden datasets sa edge
     case-om "laptopovi do 3000 EUR".
  5. Fallback u widget-u: ako schema nije ispoštovana, prikazati error +
     trigger eskalaciju (ne tih fail).
- [ ] Stale doc cleanup — security-review body + S7.3 <!-- id:stld -->
  `docs/reviews/security-review.md` body i dalje piše "🔓 OTVORENO" iako su
  V2/V3/S1/S2/S3/N2/N3 zatvoreni (vrh tabela je tačna — body je stale).
  `docs/archives/bitlab-mvp-plan.md` S7.3: kaže ⏸ ODGOĐENO; stvarno Groq-only
  ostao (`e9baa9c`) — odluka donesena drugačije od plana.
- [ ] n8n DNS workaround — staging/subpath dok ne legne pravi DNS <!-- id:n8nw -->
  `feature/n8n-deploy` (commit `d485b0a`) — kod gotov, čeka Rale-ov DNS push.
  Workaround: pustiti n8n na postojećem domenu kao subpath, ili na staging
  dok DNS ne legne. Detalji u memoriji (`project_n8n_setup_state.md`).
- [ ] Refresh `ai-search-improvements.md` sa najnovijim categories.csv + brend.json <!-- id:aisr -->
  Branislav je dostavio najnoviji export iz webshop baze na mejlu ("Ivane šaljem
  kategorije i brendove"): `data/categories.csv` (138 KB, 512 redova sa
  `parent_id` hijerarhijom — kategorije + podkategorije) i `data/brend.json`
  (phpMyAdmin format). Trenutni `docs/features/ai-search-improvements.md` opisuje
  prethodni deploy (89 kategorija, 90 brendova) — treba ažurirati brojeve i opisati
  novu kategorije/podkategorije strukturu. Koraci:
  1. Re-generisati derived fajlove: `python scripts/build_category_terms.py`
     (osvježi `data/category_terms.json`) + `python scripts/build_categories.py`
     (osvježi `data/categories.json`).
  2. Provjeriti nove brojeve (kategorije nakon <5 produkata filtera, brendovi
     iz `brend.json`) i ažurirati ai-search-improvements.md.
  3. Dodati opis hijerarhije kategorija/podkategorija (`parent_id` relationship)
     koju trenutni doc ne objašnjava.
  4. Opciono: `python scripts/embed_products.py` ako se mijenja `build_search_text`
     output (~5 min).
- [ ] Reorganizuj live docs iz `docs/` root u `docs/features/` <!-- id:dorg -->
  `docs/architecture.md`, `development.md`, `changes.md`, `Otvorena pitanja sa
  Google Drive-a.md` — svi živi i validni, ali su trenutno u `docs/` root
  umjesto u semantičkom podfolderu (`docs/features/`). Pojedinačna procjena:
  šta od ovih ide u `features/`, šta u `operations/`, šta ostaje u root-u kao
  index/entry. Lower priority, ne blokira ništa.
- [ ] Razviti safety-net testova oko ključnih funkcionalnosti i poslovne logike <!-- id:tst1 -->
  Sistematski sloj testova (unit + integracioni + regresioni + e2e) koji hvata
  regresije prije produkcije. Gradi se na postojećem — `tests/` (8 fajlova),
  `evals/` (3 runnera), `anthropic_api` marker već u `pyproject.toml` —
  konsolidacija i popuna rupa, ne greenfield. Inicijativa `tst1` živi i u
  `docs/plans/akcioni-plan.md` (Now) — ovdje high-level pointer.
  Koraci:
  1. Inventar + gap analiza — postojeći testovi/evali naspram ključne logike u
     `app/` (agent loop, rag, tools, system_prompts, faq, config, server/, storage/).
  2. Unit — popuniti rupe u poslovnoj logici: agent loop, hibridni RAG scoring +
     category filter, FAQ parsiranje, config validatori (tools/tts/voice/brand-cat
     su već pokriveni).
  3. Integracioni — komponente zajedno: agent loop + tools + rag, dashboard DB
     sloj (`requests`/`tool_calls`), `/api/dashboard/` endpointi, escalation/SMTP put.
  4. Regresioni — jedan test po dokumentovanom prošlom bugu: typo handling
     (`test_typo_robustness.py` je obrazac), halucinacija zaliha, prompt-injection,
     prazan search → escalate. Izvor bugova: `docs/reviews/` + `docs/changes.md`.
  5. E2E — golden-path kroz kanale: `/api/chat`, `/api/tts`, `/api/stt`,
     `/api/email`; `evals/run*.py` kao eval sloj.
  6. CI gate — pytest markeri (brzi unit vs spori/`anthropic_api`); mreža je
     "safety net" tek kad se pokreće automatski.
  Van scope-a: 100% coverage — fokus su poslovna logika, kritični putevi i
  dokumentovani prošli bugovi.
- [ ] Razviti i automatizovati eval framework (edge case-ovi + multi-model) <!-- id:evl1 -->
  Postojeći eval framework (`evals/run.py`, `run_categories.py`, `run_format.py`
  + datasetovi `test_questions.json`, `category_eval.json`) podići na sistematski,
  automatizovan nivo. Mjeri kvalitet AI ponašanja (accuracy, halucinacije,
  tool-calling) — komplementaran `tst1`-u, koji mjeri ispravnost koda. Koraci:
  1. Audit postojećeg — šta svaki runner mjeri, gdje su slijepe tačke, koliko su
     datasetovi reprezentativni.
  2. Edge case-ovi — proširiti datasete: typo/sleng, prazni i besmisleni upiti,
     prompt-injection, multi-turn kontekst, B2B intent, kombo proizvodi,
     van-kataloga upiti.
  3. Multi-model runner — `evals/run_models.py` (planiran u `model-eval.md`, još
     ne postoji): isti eval set kroz više modela. Umjesto plaćenih API ključeva
     koristi playwright-router `pwr` CLI — Claude.ai / ChatGPT / DeepSeek kroz Pro
     browser sesije (besplatni mjesečni resurs). Spec:
     `playwright-router/docs/pwr-broker-spec.md`.
  4. Best-practice struktura — golden datasetovi verzionisani, deterministički run,
     prag po metrici (accuracy / hallucination rate / tool-call correctness /
     latency), rezultati date-stamped u `evals/results/`.
  5. Automatizacija — eval run kao scheduled/CI korak, izvještaj se generiše sam;
     veza sa `tst1` CI gate-om. Pad ispod praga = regresija.
  Van scope-a: finalna odluka o produkcijskom modelu — to je ishod iz
  `model-eval.md`. Ovdje gradimo framework i pokrivenost, ne donosimo odluku.
- [ ] Uskladiti repo sa bitlab-standards strukturom <!-- id:std1 -->
  `docs/README.md` linkuje nazad na bitlab-standards + ostala uskladja prema
  standardu. Archive rename + konsolidacija istorijskih dokumenata su odvojeni
  u karticu `arch`. Sekundarno (Next u `akcioni-plan.md`).

## Doing

## Blocked

## Done

- [x] Rastavi LIVE.md — sav živi sadržaj u live docs, samo eventski log u archives <!-- id:live -->
  Razdvajanje po procjeni s korisnikom: SSH/restart skripte + embed snippet
  → `README.md` (sekcije "Backend restart" + "Embed snippet za webshop").
  Monitoring tabela + eskalacijski put → `docs/operations/live-beta-monitoring.md`.
  Voice migration (ElevenLabs Plan A + debugging hidden voice button +
  vraćanje voice-a koraci) → `docs/voice.md`. "Šta je novo backend-side" —
  duplikat `docs/features/ai-search-improvements.md`, samo referenca ostala.
  U arhivi (`docs/archives/live-2026-05-08.md`) ostao samo eventski log:
  header, odluka tog dana, šta se mijenja u 11:00, ishod. `LIVE.md` obrisan
  (`git rm`). Reference u `akcioni-plan.md` (5x) ažurirane; `stld` sužen.
- [x] Konsolidacija istorijskih dokumenata → `docs/archives/` <!-- id:arch -->
  Premješteno u `docs/archives/` (`git mv`, history očuvana, 47 fajlova):
  `docs/handoff/`, `docs/dan4/`, `design_handoff_conduit/` (root),
  `docs/BitLab-AI-Asistent-Dizajn/`. Drugi prolaz (`architecture.md`,
  `development.md`, `changes.md`, `Otvorena pitanja…md`): svi procijenjeni
  kao live — kandidati za reorganizaciju (`dorg` kartica), ne arhivu.
  `LIVE.md` razdvojen kroz `live` ticket. Zadržano kao live: `docs/brainstorm/`.
- [x] Repo scanner skripta (`scan.sh`) za web chat / Devin analize <!-- id:scan -->
  `scan.sh` kopiran iz `bitlab-standards`, header naslova promijenjen na
  "BitLab AI Asistent", `repo-scan.md` dodat u `.gitignore`. Skripta testirana —
  generiše ~50k linija / 10 MB output (194 fajla) sa strukturom + sadržajem
  svih tracked tekstualnih fajlova. Spremno za web chat / Devin paste.
- [x] Reverse-engineering arhive → `docs/plans/akcioni-plan.md` <!-- id:rev1 -->
  Verifikacija završena (kod + git, ne tvrdnje dokumenata): 6 inicijativa
  Completed, 2 Now (`p1fix`, `tst1`), 3 Next (`meval`, `grow1`, `std1`),
  6 Later. Now inicijativa `p1fix` decomposed u 4 nove STATUS taske
  (`p1fx`, `p2cs`, `stld`, `n8nw`). Akcioni plan na `docs/plans/akcioni-plan.md`.
- [x] STATUS.md kreiran prema bitlab-standards shemi <!-- id:bas1 -->
  Frontmatter + Todo/Doing/Blocked/Done kolone; prolazi `validate-status.py`.

## Poznata ograničenja

- Istorijski završen rad (MVP, Sesija 6 n8n, Sesija 7 polish, Sesija 8
  dashboard, LIVE test 2026-05-08, git + standards konsolidacija) živi kao
  Completed inicijative u `docs/plans/akcioni-plan.md`, ne kao Done kartice
  ovdje. STATUS.md drži tekuće taktičke taske, ne cijelu istoriju projekta.
- `tst1` / `evl1` / `std1` su istovremeno STATUS taske i inicijative u
  `akcioni-plan.md`. Dvostruko predstavljanje je svjestan kompromis dok
  cm-viewer Roadmap view ne počne grupisati taske po inicijativi
  (`init:` referenca u shemi — sad ne podržana validator-om).
- Nema lokalnog validatora u repou — shema se provjerava sa
  `bitlab-standards/scripts/validate-status.py`. Kopija u `scripts/` je
  opciona, vezana za `std1`.
