# Lessons learned — bitlab-ai-asistent

Destilovane lekcije iz projekta. Svaka = **jedna poenta** na vrhu, pa kratak dvodio, pa link na detalje.
Sirove napomene/zanimljivosti idu u [`notes.md`](notes.md).

---

## L1 — Ralph autonomni loop: sjajan do zida, pa unazad

**Poenta:** Autonomni loop je *sam* digao eval ~56% → 84% gradeći prompt od nule, ali kad je rješenje
tražilo tehničku promjenu (forsiran tool calling) koju dotad nije "vidio", krenuo je **unazad**
(84% → 79%) — jer gejtuje na lažnom signalu i sam committa. Čovjek je preuzeo dijagnozu + arhitekturni
fix → **96%**.

### Dio 1 — Šta je petlja uradila sama (autonomno)
- Krenuli od nule; loop sam piše prompt, dodaje pravila, pokreće testove.
- Sam digao rezultat: **~56% → 84% (iter8)** — bolji od ručnog starta.
- Zatim sam dodao `category_overview` pravila → počeo da pada.
- 36h / 22 iteracije; do **iter17 = 79,2%**. Faktički "napredovao unazad".
- Zašto unazad: gejtovao na malom random sample-u (lažni zeleni 93–100%) dok je pun set bio 79%; i sam je commitao svaku prompt izmjenu.

### Dio 2 — Šta je čovjek morao ručno
- Pauza petlje → ručna dijagnoza (vidi link): svih **29/29 regresija = model NE zove tool, halucinira katalog** (cijene, URL-ovi). Uzrok je tehnički, ne prozni — nema **forsiranog tool calla** + prompt pretrpan imperativima ("OBAVEZNO", "ZABRANJENO").
- Fix je arhitekturni (mehanička garancija), ne dalje štelovanje proze: treći tool `respond_to_user` + `tool_choice` (required/any) + `category_id` enum + `temperature=0`.
- Rezultat: **96,0%** — acceptance prag ≥95% oboren.

**Lekcija:** Ralph je sjajan za iterativno građenje i za *otkrivanje* problema korak-po-korak (sam je doveo do 84% i pokazao gdje puca). Ali za suptilni/arhitekturni trade-off (forsiran tool, prompt overload) treba **čovjek-u-petlji + pun eval kao gate**, ne autonomni loop na sample signalu. Ralph → mehanički rad (refactor, dodavanje testova); čovjek → arhitektura i suptilna prompt-ekonomija.

Putanja: 56% → 84% (iter8, loop) → 79% (iter17, regresija) → **96%** (ručni forsiran tool).

Detaljna analiza (brojevi, konkretni slučajevi): [`../archives/EVAL_REGRESIJA_iter17.md`](../archives/EVAL_REGRESIJA_iter17.md)

---

## L2 — Verdict cache po prompt-hashu: resume bez ponovnog troška

**Poenta:** Eval framework kešira verdikt po `(entry, prompt_hash, tools_hash)` i **default je uključen**.
Ako run pukne na pola (rate-limit, greška), ponovni run **ne troši PWR sesiju** na entry-je koji su već
prošli — kreće efektivno od prvog neobrađenog. Promijeniš `SYSTEM_PROMPT_V1` ili tool → hash se mijenja →
keš se **automatski invalidira** (nema stale verdikta). Popraviš jedan entry → invalidira se samo taj.

- Implementirano i živo: `evals/cache/<sha256>.json` (stotine keširanih verdikata), `--no-cache` bypass,
  `--cache-stats` pregled (vidi [`ralph/AGENTS.md`](../../ralph/AGENTS.md), linije 21-22 i 64).
- Win: 80-90% štednje od druge iteracije naovamo — zato je sigurno iterirati prompt bez straha od cijene re-runa.

**Lekcija:** keširanje po sadržaj-hashu sa auto-invalidacijom je *temelj* jeftine eval-iteracije; bez njega
svaki resume samo razmazuje trošak umjesto da ga eliminiše.
