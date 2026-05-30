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
updated: 2026-05-29
---

# STATUS — bitlab-ai-asistent

Taktički Kanban (kartice = konkretne taske). Strateške inicijative i horizonti su u
[`docs/plans/akcioni-plan.md`](docs/plans/akcioni-plan.md). Temeljna pravila (TDD zero-base,
eval invariant) u [`PLAN.md`](PLAN.md). Ralph autonomni-loop plan: `ralph/IMPLEMENTATION_PLAN.md`
(zaseban; vidi `evfx` open pitanje da li ga nastavljamo).

**Princip za eval-fix kartice (`rvpr`/`frtl`/`tght`): razvoj na HARD dev-uzorku, pun eval tek na kraju.**
Iteriraj prompt na `categories_dev` suite-u (29 poznatih iter17 fail-ova + negativci, vidi `dsmp`):
`python -m evals.framework.runner --suite categories_dev --mode full` — ~37 poziva, brzo i jeftino.
Pun eval (250, `--suite categories --mode full`, ~15h) ide JEDNOM, u `acpt`, kao acceptance vs iter8
baseline-om (84.4%). NE gejtuj svaku karticu punim eval-om (skupo/lijeno), NITI random `--mode sample`
(30): po `EVAL_REGRESIJA_iter17.md` dao je lažni zeleni 93-100% dok je pun bio 79% — stratifikuje po
parent/leaf tagu, ne po težini, pa promaši baš slučajeve koji pucaju. `scripts/smoke.py` je za eyeball
(bez ocjene). Jedan fix u trenutku; ništa ne smije da padne na dev-uzorku.

## Todo

- [ ] Stezanje — niska temperatura + category_id enum <!-- id:tght -->
  `temperature≈0` u oba `create()` (novi config setting); `category_id` enum (validni ID-evi)
  u tool schemi. Svaka pod-izmjena zasebno mjerena. Gate: dev-uzorak (`--suite categories_dev --mode full`).
- [ ] Acceptance — pun eval (250) JEDNOM, ≥95% ili svjesna ship odluka <!-- id:acpt -->
  Tek kad je dev-uzorak (`dsmp`) zelen, pokreni PUN eval JEDNOM: `--suite categories --mode full`
  (250, ~15h) vs baseline 84.4%. Cilj ≥95%, ILI eksplicitna odluka o ship-u na ~85% sa low-confidence
  fallback-om ("nisam siguran, evo opcija") za dvosmislene slučajeve.

## Doing

## Blocked

## Done

- [x] Dev eval suite — hard uzorak (dsmp) <!-- id:dsmp -->
  `scripts/gen_dev_sample.py` (regenerabilan) → `evals/sets/categories_dev.jsonl`: 29 iter17
  PASS→FAIL + 8 negativaca = 37. Canonical netaknut. Brzi/jeftin gate (~5min) umjesto punog eval-a.
- [x] Lean prompt u SYSTEM_PROMPT_V1 — rvpr (spojen sa frtl) <!-- id:rvpr -->
  Lean leaf/parent logika u `SYSTEM_PROMPT_V1`; kraj divergencije (agent/eval/keš jedan prompt).
  Spike `LEAN_KERNEL_PROMPT` uklonjen. Odrađeno u istom potezu sa `frtl` (jedna izmjera, ne duplo).
- [x] Forsiran tool calling — respond_to_user + tool_choice <!-- id:frtl -->
  `RESPOND_TO_USER_TOOL` u `app/tools.py`; `tool_choice` any (Anthropic) / required (PWR) + loop
  intercept (`respond_to_user` → reply, van `captured_tool_calls`). Rezultat na dev-uzorku:
  **91.9% (34/37)** — 27/29 regresija vaskrslo (bilo 0), 7/8 negativaca. Ostalo: 1 timeout (infra),
  1 leaf-miss (`cat-leaf-175`, fali leaf-priority).
- [x] Smoke eyeball — scripts/smoke.py <!-- id:setp -->
  Pokrenut na 4 upita: 3/3 kataloška → pravi tool + smisleni args; prazan rezultat prijavljen
  pošteno (bez halucinacije); out-of-scope ("vrijeme") → bez toola. Nalaz: PWR `tool_choice=required`
  je mekan (model apstinirao na OOS u 1 iteraciji) — tvrda garancija ide kroz `frtl`. (`search_products`
  je stub `{"products":[]}` do Faze 2 — ne utiče na routing eval.)
- [x] Eval regresija iter17 — dijagnoza <!-- id:i17r -->
  Pun A/B (iter8 84.4% vs iter17 79.2%, 212 zajedničkih): 29/29 regresija = apstinencija
  toola (model halucinira katalog), nula mis-routinga. Uzrok: proza ("OBAVEZNO") umjesto
  mehaničke garancije. Doc: `EVAL_REGRESIJA_iter17.md`, `docs/PROMPT-BEST-PRACTICES.md`.
- [x] Faza 0 — Ralph petlja + TDD eval framework infra <!-- id:fz00 -->
  2026-05-24. Test piramide sa mock_anthropic, CI/e2e/eval-nightly workflows, pre-commit,
  `ralph/` state files, `evals/framework/` runner sa parser-based judge.

## Poznata ograničenja

- PWR `tool_choice="required"` je soft-enforcement (ReAct preamble + parsiranje, bez retry),
  ne tvrda garancija — zato je "Opus 4.8 pouzdano zove tool" pretpostavka koju testira
  dev-uzorak pa pun eval, a Anthropic-native `{"type":"any"}` je tvrdi fallback (vidi `frtl`).
- Acceptance ≥95% je inicijalni bar; otvoreno je li ship-able na ~85% sa fallback-om.
- `cat-manual-typo-raunari`: model auto-koriguje "raunari" → "Računari" i rutira (expect=null →
  routing FAIL). Svjesno PRIHVAĆENO kao OK ponašanje (korisnička odluka); case se NE dira, taj FAIL
  ne računamo kao naš problem.
