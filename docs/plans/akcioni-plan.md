---
sections:
  - id: now
    name: Now
  - id: next
    name: Next
  - id: later
    name: Later
  - id: completed
    name: Completed
---

# Akcioni plan — bitlab-ai-asistent

Ažurirano: 2026-05-29

> Strateški plan (Now/Next/Later inicijative). Taktičke taske su u [`../../STATUS.md`](../../STATUS.md).
> Format: [`bitlab-standards/docs/standards/akcioni-plan-schema.md`]. Temeljna strategija
> (TDD zero-base reset) u [`../../PLAN.md`](../../PLAN.md).

---

## Now

### Popravka eval regresije → kategorije eval na acceptance <!-- id:evfx -->

Vrati categories eval sa 79.2% (iter17 regresija) na baseline ~85%, pa hirurški do
acceptance (≥95%) forsiranjem tool callinga po standardu: revive prompt → `respond_to_user`
+ `tool_choice` → stezanje (temp + enum). Fix je arhitekturni (mehanička garancija tool
poziva), ne dalje štelovanje proze.

Started: 2026-05-29

**Princip — ništa ne smije da padne; razvoj na hard uzorku, pun eval na kraju.**
Iteriraj na dev-uzorku poznatih teških slučajeva (`categories_dev`: 29 iter17 fail-ova + negativci),
ne na punom — pun je ~15h i skup. Pun eval (`--suite categories --mode full`, 250) ide JEDNOM, kao
acceptance vs iter8 baseline-om (84.4%). NE koristi random `--mode sample` (30 po tagu) za gejt: dao
je lažni zeleni 93-100% dok je pun bio 79% (`EVAL_REGRESIJA_iter17.md`) — promaši baš teške leaf
slučajeve. Regresija na dev-uzorku → STOP: revert, ILI (ako je test loš) zasebna "fix test set"
taska prije nastavka. Jedan fix u trenutku.

**Scope:**
- Revive `bck/app/system_prompts.py` kao bazu prompta (čista leaf/parent logika 1/1a/1b).
- Forsiran tool calling: `respond_to_user` (cookbook "tool required" pattern) + `tool_choice`.
  Default = PWR `required` (cost odluka), Anthropic-native `{"type":"any"}` je fallback.
- Niska temperatura + `category_id` enum u tool schemi.

**Out of scope:**
- Faza 2 (products RAG) i Faza 3 (cross-reference) — Next.
- Multi-channel prompt (voice/email format) iz bck — nije u categories eval scope-u.

**Veza sa STATUS:** kartice `dsmp`, `rvpr`, `frtl`, `tght`, `acpt` u `STATUS.md` Todo.
Otvoreno: je li Ralph autonomni loop uopšte potreban uz forsiran tool + schemu, ili je
dovoljan jedan čist rebuild + pun eval.

---

## Next

### Faza 2 — Eval za proizvode (RAG search_products) <!-- id:fza2 -->

Pravi RAG za `search_products` sa katalogom. Spec: `specs/products.md`.
Cherry-pick iz `bck/app/rag.py`.

### Faza 3 — Cross-reference (multi-tool sekvence) <!-- id:fza3 -->

Multi-tool sekvence preko više upita. Spec: `specs/cross-reference.md`.

---

## Later

### Voice modul (faster-whisper) povratak iz bck <!-- id:voic -->

### Email auto-reply povratak iz bck <!-- id:emal -->

### Dashboard frontend (dashboard/) povratak <!-- id:dash -->

### N8N integracije <!-- id:n8ni -->

Vidi memoriju `project_n8n_setup_state`.

---

## Completed

### bitlab-standards adopcija — STATUS + akcioni-plan <!-- id:stda -->

Završeno: 2026-05-29

`STATUS.md` preveden u taktički Kanban po shemi (kartice + stabilni ID-evi, validira
`validate-status.py`); ovaj `akcioni-plan.md` kreiran kao strateški sloj. Time je
ispunjena pilot-taska iz `bitlab-standards` Now inicijative (`rollt`).

### Faza 0 — Ralph petlja + TDD eval framework infra <!-- id:fza0 -->

Završeno: 2026-05-24

Petlja, prompts, test piramide (`tests/{unit,integration,e2e,regression}/`),
CI/e2e/eval-nightly, pre-commit, `ralph/` state, `evals/framework/` runner + parser judge.
(Detalji u `STATUS.md` kartica `fz00`.)
