# Backlog — bitlab-ai-asistent

**Memorija / inbox.** Prioriteti prate board. Lekcije → [`lessons-learned.md`](lessons-learned.md) · zapažanja → [`notes.md`](notes.md).

---

## Prioritet 1 — Akcioni plan (Now/Next/Later)  ·  *board P1, u toku*

Kartice, redoslijedom izvršavanja:

1. **RAG `search_products`** — pravi RAG; bira po query-ju (ne tačnom ID-u), rješava dio leaf-precision padova. Spec [`../../specs/products.md`](../../specs/products.md) je tanak (11 lin) → **proširiti prije dekompozicije**.
2. **Izvlačenje poslovne logike iz `bck/` → produkcija** — sistematski po [`baseline-i-restore.md`](baseline-i-restore.md) + repo-inventory; app završena, samo izvući postojeće i popraviti za produkciju.
3. **Preostali padovi testova (7/15)** — *analizirano: nije prompt-fixing; mapira se na Faza 2 / known-limit.* Vidi [`../work/2026-05-29-eval-acceptance/nalaz-fail-set-enum-temp.md`](../work/2026-05-29-eval-acceptance/nalaz-fail-set-enum-temp.md).
4. **Prompt caching** — `cache_control:{"type":"ephemeral"}` na zadnjem tool bloku ([`../../app/agent.py`](../../app/agent.py)) → ~90% uštede na cached dijelu. Izvor [`../archives/EVAL_OPTIMIZACIJA.md`](../archives/EVAL_OPTIMIZACIJA.md) Q1 #4.
5. **Prompt injection — zaštita + eval test** — agent NE smije odati ključeve/API kad ga neko pokuša izvući. Primjeri već postoje u `bck/` promptu → ekstraktovati. Dodati i evaluation test za injection.
6. **FAQ (frequently asked questions)** — vratiti/odraditi FAQ odgovore.
7. **Edge case-ovi + eval testovi za sve toolove** — `category_overview`, `search_products`, baza znanja, FAQ, `respond_to_user`. Edge case-ove **nalazimo kroz eval testove**; **pokrenuti sve (uklj. regresiju)** da nema regresije kako dodajemo u prompt. **Pregledati cijeli `bck/` prompt** da se nijedan slučaj ne zaboravi.
8. **Novi set testova za sve toolove** — napraviti bazu testova / novu evaluaciju za svaki tool i svaku kategoriju (baza za `search_products` + po kategoriji), da se sve "sito i rešeto" ispretrese i radi perfektno.
9. **UI po JSON šemi** *(zaboravljeni dio)* — sad agent generiše UI/layout po specifikaciji; promijeniti tako da mu se pošalje **JSON šema**, agent vraća samo **JSON podatke**, a layout se renderuje na widgetu (frontend).
10. **Kategorije klikabilne na widgetu** — sad se listaju kao čipovi/kartice ali nisu klikabilne; treba da budu **klikabilne + s ikonicama**.

---

## Prioritet 2 — Procjena efforta  ·  *board P2*

- Svakoj kartici iz Prioriteta 1 ocijeni effort 4-dim modelom (A/B/J/V) → `effort:N pct:PP` (skill `estimate-effort-level`).

---

## Prioritet 3 — Burndown chart  ·  *board P3*

- Agregiraj `pct` težine kroz vrijeme (Done = spaljeno, Todo = preostalo) do kraja projekta. "Treći repozitorijum" = TBD. Srodno: `weekly-effort`.

---

## Prioritet 4 — Evaluation Framework  ·  *board P4*

Komponenta: dorada eval infrastrukture. Izvor: [`../archives/EVAL_OPTIMIZACIJA.md`](../archives/EVAL_OPTIMIZACIJA.md) + review grane `feat/ralph-categories-eval-fix`.

- Paralelni / concurrent eval pozivi — `asyncio.gather` (~4× brže).
- Self-aware session limit — reaktivni 429 + checkpoint/resume; proaktivni token brojač (5h prozor).
- Error handling — rate-limit false-positive: [`../../app/main.py`](../../app/main.py) nema 429 handler → 429 ispadne 500 → FAIL.
- Bug: kombinacije flagova netestirane (`--limit` + `--mode` + …); `--limit 25` je guess.
- Partial verdicts ne agregiraju — treba `parts/` + `merge_parts.py`.

---

## Prioritet 5 — Ralph petlja  ·  *board P5*

Komponenta: **self-correcting / self-building software** (razviti zasebno).

**Industrijski naziv (za CV):** *autonomous, eval-gated **self-improving LLM agent loop*** ("Ralph" tehnika) —
coding agent koji iterativno piše → testira → commita protiv automated eval harness-a, uz verdict-cache,
checkpoint/resume i CI-gated commit. Kategorija: **agentic AI / autonomno softversko inženjerstvo**.
Mehanika petlje: [`../../ralph/AGENTS.md`](../../ralph/AGENTS.md).

---

## Prioritet 6 — Dodavanje ostalih tool-ova (iz `bck/`)

Vraćanje preostalih komponenti iz `bck/` (vidi [`baseline-i-restore.md`](baseline-i-restore.md)):

- **n8n email automatizacija** — email auto-reply tok.
- **Voice chat** — glasovni modul.
- **Sinhronizacija baze** — cron job direktno na BitLab bazu i WebShop; **vektorski indeks** se generiše automatski (dnevno).
- **Autentifikacija na dashboard** — trenutno je čist HTML, dodati auth.
- **Dashboard — poboljšati + ispeglati bugove** (bitlab-ai-asistent dashboard).
- **Search-more proizvoda** — prikaz "još", da se cijeli katalog može pregledati kroz AI agenta.
- **Prompt sanitization** — čišćenje / validacija korisničkog ulaza prije slanja modelu. *(premješteno iz P1)*
