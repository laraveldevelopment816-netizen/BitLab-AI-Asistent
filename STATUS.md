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

**Princip za eval-fix kartice (`rvpr`/`frtl`/`tght`/`acpt`): ništa ne smije da padne.**
Svaka kartica se gejtuje PUNIM eval-om (`python -m evals.framework.runner --suite categories --mode full`)
i poredi sa iter8 baseline-om (84.4%). Regresija → STOP: revert izmjene, ili (ako je test loš)
otvori zasebnu "fix test set" karticu prije nastavka. Jedan fix u trenutku — mjeri svaki zasebno.

## Todo

- [ ] Setup arhitekture / sneak-peek — jedan poziv (tool_choice + zdrav prompt) <!-- id:setp -->
  Predzadatak (spike, NIJE eval-gated): u `app/agent.py` dodaj `tool_choice` (PWR `required` na
  `chat.completions.create`, Anthropic `{"type":"any"}` na `messages.create`) i privremeno
  zamijeni `SYSTEM_PROMPT_V1` zdravim promptom (BITLAB_BASE routing iz `bck/app/system_prompts.py`,
  bez Group A+B). Napravi JEDAN smoke poziv i prijavi: zove li model tool, broj iteracija, šta
  vraća. Cilj: ući u kod + vidjeti ponašanje uživo prije rigoroznih gated koraka. Bez commita,
  bez diranja eval setova. Rigorozno mjerenje ide u `rvpr` (prompt) pa `frtl` (tool) zasebno.
- [ ] Revive system prompt iz bck — samo prompt, bez forsiranja toola <!-- id:rvpr -->
  Zamijeni naduveni `SYSTEM_PROMPT_V1` (`app/agent.py:38-96`) čistom leaf/parent logikom iz
  `bck/app/system_prompts.py` (pravila 1/1a/1b). Bez Group A+B, bez alata kojih ovdje nema
  (`get_faq`/`check_availability`/`escalate`), bez channel formata. Gate: smoke (1 poziv) →
  pun eval; očekivano nazad na ~84-86%, nula novih regresija.
- [ ] Forsiraj tool calling — respond_to_user + tool_choice <!-- id:frtl -->
  `RESPOND_TO_USER_TOOL` u `app/tools.py`; `tool_choice` (PWR `required`, Anthropic
  `{"type":"any"}` fallback) u oba runnera; loop intercept: `respond_to_user` → reply, van
  `captured_tool_calls`, break. Negativni upiti ostaju PASS (model zove samo `respond_to_user`
  → `tool_calls` prazan → judge PASS). Gate: pun eval.
- [ ] Stezanje — niska temperatura + category_id enum <!-- id:tght -->
  `temperature≈0` u oba `create()` (novi config setting); `category_id` enum (validni ID-evi)
  u tool schemi. Svaka pod-izmjena zasebno mjerena. Gate: pun eval.
- [ ] Acceptance — ≥95% ili svjesna ship odluka <!-- id:acpt -->
  Dovedi pun eval na ≥95%, ILI eksplicitna odluka o ship-u na ~85% sa low-confidence
  fallback-om ("nisam siguran, evo opcija") za dvosmislene slučajeve.

## Doing

## Blocked

## Done

- [x] Eval regresija iter17 — dijagnoza <!-- id:i17r -->
  Pun A/B (iter8 84.4% vs iter17 79.2%, 212 zajedničkih): 29/29 regresija = apstinencija
  toola (model halucinira katalog), nula mis-routinga. Uzrok: proza ("OBAVEZNO") umjesto
  mehaničke garancije. Doc: `EVAL_REGRESIJA_iter17.md`, `docs/PROMPT-BEST-PRACTICES.md`.
- [x] Faza 0 — Ralph petlja + TDD eval framework infra <!-- id:fz00 -->
  2026-05-24. Test piramide sa mock_anthropic, CI/e2e/eval-nightly workflows, pre-commit,
  `ralph/` state files, `evals/framework/` runner sa parser-based judge.

## Poznata ograničenja

- PWR `tool_choice="required"` je soft-enforcement (ReAct preamble + parsiranje, bez retry),
  ne tvrda garancija — zato je "Opus 4.8 pouzdano zove tool" pretpostavka koju testira pun
  eval, a Anthropic-native `{"type":"any"}` je tvrdi fallback (vidi `frtl`).
- Acceptance ≥95% je inicijalni bar; otvoreno je li ship-able na ~85% sa fallback-om.
