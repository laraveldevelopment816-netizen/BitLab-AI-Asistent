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

Ažurirano: 2026-05-15

Taktički nivo (dnevne taske) prema bitlab-standards shemi
(`bitlab-standards/docs/standards/status-schema.md`). Strateški nivo —
inicijative Now/Next/Later — živi u `docs/plans/akcioni-plan.md`; taj fajl
još ne postoji, pravi ga prva taska (`rev1`).

## Todo

- [ ] Reverse-engineering arhive → `docs/plans/akcioni-plan.md` <!-- id:rev1 -->
  Proći kroz plan-dokumente, utvrditi šta je STVARNO urađeno (dokaz iz
  `git log` + koda, ne iz tvrdnje u dokumentu), pa otvorene + nove stavke
  složiti u strateški akcioni plan. Koraci:
  1. Izvori: `docs/archive/bitlab-mvp-plan.md` (Sesije 0–7),
     `docs/plans/production-prep.md` (S8), `docs/plans/model-eval.md` (S9),
     `docs/plans/growth.md` (S10), `LIVE.md`, `docs/changes.md`, `docs/reviews/`.
  2. Svaku numerisanu tačku/sesiju označiti: urađeno / djelimično / otvoreno.
  3. Otvorene + nove stavke u `docs/plans/akcioni-plan.md` po Now/Next/Later.
  4. "Now" inicijativu razbiti u konkretne taske ovdje u Todo (decompose).
- [ ] Razviti safety-net testova oko ključnih funkcionalnosti i poslovne logike <!-- id:tst1 -->
  Sistematski sloj testova (unit + integracioni + regresioni + e2e) koji hvata
  regresije prije produkcije. Gradi se na postojećem — `tests/` (8 fajlova),
  `evals/` (3 runnera), `anthropic_api` marker već u `pyproject.toml` —
  konsolidacija i popuna rupa, ne greenfield. Obim je inicijativa-veličine:
  nakon `rev1` vjerovatno seli u `akcioni-plan.md` kao zasebna inicijativa.
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
  `docs/archive/` → `docs/archives/` (standard traži množinu); `docs/README.md`
  linkuje nazad na bitlab-standards. Sekundarno — ne blokira `rev1`.

## Doing

## Blocked

## Done

- [x] STATUS.md kreiran prema bitlab-standards shemi <!-- id:bas1 -->
  Frontmatter + Todo/Doing/Blocked/Done kolone; prolazi `validate-status.py`.

## Poznata ograničenja

- `docs/plans/akcioni-plan.md` (strateški nivo) još ne postoji — popunjava ga
  `rev1`. Do tada je ovo jedini nivo praćenja.
- Istorijski završen rad (MVP Sesije 0–7, Sesija 8 dashboard, LIVE test
  2026-05-08) namjerno NIJE unesen kao Done kartice — `rev1` ga verifikuje
  kroz git + kod i rekonstruiše u akcioni-plan. STATUS.md drži samo tekuće
  taktičke taske, ne cijelu istoriju projekta.
- Nema lokalnog validatora u repou — shema se provjerava sa
  `bitlab-standards/scripts/validate-status.py`. Kopija u `scripts/` je
  opciona, vezana za `std1`.
