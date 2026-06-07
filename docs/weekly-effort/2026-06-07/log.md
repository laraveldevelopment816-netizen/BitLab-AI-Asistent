# Weekly Effort — log (činjenice iz gita)

**Prozor:** ned 31.05.2026 → ned 07.06.2026 (zadnjih 7 dana, `--since="7 days ago"`).
**Izvor:** isključivo `git log --all` po repou + `git status`/mtime za uncommitted. Bez utiska, bez sjećanja.
**Autor:** sve Ivan Kukic (identiteti spojeni: `Ivan Kukic <ivan.kukic@gmail.com>` + `Kule <noreply@anthropic.com>` = jedan autor). Bez vanjskih saradnika u prozoru.

---

## Repo set (otkriveno + deduplikovano)

PROJECTS root: `/mnt/c/Users/Kule/Projects` · `find -maxdepth 3 -name .git` → 24 git foldera.
Aktivnost u prozoru ima **5 logičkih repoa** (ostalih 19 — 0 commit-a):

| Repo | Commit-i u prozoru | Napomena |
|---|---:|---|
| bitlab-ai-asistent | 21 | (+3 stash ref-a, ne broje se) |
| bitlab-standards | 17 | |
| people-first | 7 | |
| cm-viewer | 3 | + **uncommitted** (vidi dolje) |
| cm-scraper | 1 | deduplikovano iz 3 klona |

**Dedup:** `cm-scraper`, `cm-scraper-v0`, `cm-scraper-v1-cli-pipeline` → isti origin (`gitlab.com:tech-talent-connect/cm-scraper.git`) + **isti commit** `ebaba98` → jedan logički repo, jedan commit.

**Ukupno: 49 stvarnih commit-a / 5 repoa / 7 dana** (3 stash ref-a izuzeta).

---

## Faktografski timeline po danima (spojeno kroz repoe)

| Dan | Commit-i | Repoi | Šta |
|---|---:|---|---|
| **ned 31.05** | 19 | 3 | bitlab-ai: acceptance run **94,0%**, leaf-priority fix (8 leaf-vs-parent kolizija), leaf-tune dataset, boardovi · bitlab-standards: `/work` skill nastao, rename `work-session-bootstrap→work` i `update-status→synchronize-status`, CHEATSHEET regen · cm-viewer: Kanban kartice (fade/expand, fullscreen, srednji klik→tab) |
| **pon 01.06** | 1 | 1 | cm-scraper: bootstrap `STATUS.md` + akcioni-plan (jedini mirniji dan) |
| **uto 02.06** | 6 | 2 | bitlab-standards: `/work` board + auto-open browsera, `gen-cheatsheet-pdf --src` · people-first: review sesija 02.06, **studija „kako mjeriti težinu zadatka"**, ralph-loop logovi, voice single-source language + cross-platform putanje |
| **sri 03.06** | 4 | **4** | **EFFORT-LEVEL sistem sleće u 4 repoa istovremeno @01:29–01:30** — standard+validator+skills+migracija (standards), effort kartice na svim STATUS (bitlab-ai), studija/plan/migration notes (people-first), parser+API+meter bar (cm-viewer) |
| **čet 04.06** | 0 (git) | — | Kalendarski prazan u gitu, ALI: enum/temperature rad sleteo **pet 00:52** (= čet noć), a sesija `2026-06-04-stord-aplikacija` commit-ovana tek **07.06**. Stvarno NIJE prazan dan. |
| **pet 05.06** | 2 | 1 | bitlab-ai @00:52: `category_id` enum + **temperature stezanje** (toggle) + fail-set + nalaz enum-temp run |
| **sub 06.06** | 3 (+stash) | 1 | bitlab-ai: `run_acceptance.sh` batch runner (~80/prozor), enum guardrail, **typo eksperiment stashed/revertovan** iz acceptance (parkiran kandidat), arhiviranje run artefakata |
| **ned 07.06** | 14 | 3 | bitlab-ai: full eval **250 → re-run 3 infra-timeouta → 96,0% (240/250) acceptance ZATVOREN**, repo-map + dvojezični repo-inventory, board sync · bitlab-standards: 4 `assess-effort-*` sub-skilla + `estimate-effort-level` orkestrator + formula/eval skripte + test + CHEATSHEET + README install · people-first: stord CV + cover (Forward Deployed Engineer), agent-sdk/workflow istraga |

**Najteži dani:** ned 31.05 (19c) i ned 07.06 (14c). **Najmirniji:** pon 01.06 (1c). **Jedini „prazan" u kalendaru** (čet 04.06) je artefakt commit-boundary-ja, ne neradni dan.

---

## Effort po workstream-u (4-dim model + git dokaz)

Skala/formula: `raw = 0.30·A + 0.30·J + 0.20·B + 0.20·V` · `pct = round(20 + (raw−1)/4·79)` · nivo iz pct.
A=Nejasnoća, J=Prosuđivanje, B=Domet/nepovratnost, V=Neprovjerljivost (svaka 1–5). Standard: `bitlab-standards/docs/standards/effort-measurement.md`.

| # | Workstream (repo) | A | J | B | V | raw | **pct** | **L** | Git dokaz |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|---|
| 1 | **Effort-level mjerni sistem** (bitlab-standards) | 5 | 5 | 4 | 4 | 4.6 | **91%** | **5** | `ccac7b0` standard+validator+migracija; `cea182f` 4 assess sub-skille + formula/eval skripte; `7771f5a` estimate orkestrator; `test_validate_status.py` +71. Wicked problem (kako mjeriti težinu), cross-repo standard, model nefalsifikabilan. |
| 2 | **Categories eval → 96% acceptance** (bitlab-ai) | 3 | 4 | 3 | 2 | 3.1 | **61%** | **3** | `d16b8ab` leaf-priority (8 kolizija); `cdb2685` enum+temperature toggle; `2717f13` 94% → `e61e205` **96,0% (240/250)**. `app/tools.py` +38 (mali diff, visok judgment); najprovjerljiviji WS (mjerljiv broj). |
| 3 | **`/work` skill + živi board + renames** (bitlab-standards) | 3 | 3 | 2 | 3 | 2.8 | **56%** | **3** | `2ce83ae` work-session start; `a8f2041`/`05601ae` renames; `b664110` auto-open board; `gen-cheatsheet-pdf.py` +184. Izvršavanje poznatog board patterna. |
| 4 | **Brainstorm / strategija** (people-first) | 2 | 4 | 1 | 4 | 2.8 | **56%** | **3** | `5b780ab` review+model težine; `973ba7e` effort studija (seme WS#1); `0e430ac` agent-sdk istraga; `89432e9` stord CV (FDE). +1049/−4, gotovo sve docs; visok judgment/neprovjerljivost, nizak domet. |
| 5 | **STATUS Kanban + effort meter** (cm-viewer) | 2 | 3 | 2 | 3 | 2.5 | **50%** | **2** | `43abcc9` kartice fade/expand+fullscreen; `72b1254` effort parser+API+meter bar; `test_status_parser.py` +67. `StatusKanban.tsx` +218. Frontend zanat, AI puno pomaže. |
| 6 | **STATUS bootstrap** (cm-scraper) | 1 | 2 | 1 | 2 | 1.5 | **30%** | **1** | `ebaba98` bootstrap iz template-a, 1 commit. Meta/process, trivijalno. |

**Dominantna nit sedmice:** workstream #1 (effort-mjerni sistem) — najteži zadatak (L5), i ujedno **cross-repo tema** koja je 03.06 sletjela u 4 repoa odjednom + nastavljena 07.06 dekompozicijom na sub-skille.

---

## Uncommitted rad (git-log ga NE vidi)

- **cm-viewer** — 5 izmijenjenih (`StatusKanban.tsx`, `status_parser.py`, `schemas/status.py`, `api.ts`, `STATUS.md`) +48/−28, + untracked `docs/work/`. **mtime 03.06** → stoji necommit-ovano ~4 dana (nastavak effort-meter rada). Sitno ali ustajalo: finiširaj ili stash-uj.
- **bitlab-ai-asistent** — 06.06 typo-eksperiment u stash-u (`eba9a11`), namjerno revertovan iz acceptance, parkiran kao kasniji kandidat.
- Ostala 4 aktivna repoa: čista radna stabla.

---

## Nalazi (iskreno)

1. **Dvije velike niti, ne jedna.** (a) Prebacivanje categories routing agenta preko praga ≥95% acceptance → **zatvoreno na 96,0% (240/250)** u bitlab-ai; (b) izgradnja **effort-mjernog standarda + tooling-a** u bitlab-standards (najteži pojedinačni zadatak, L5). Sati su otišli podjednako na isporuku i na meta/mjerenje.

2. **Bila je to tooling-and-measurement sedmica, ne feature sedmica.** Stvarna promjena u PROIZVODU (kategorizacija glasovnog agenta) je **mali diff** u `app/tools.py` (~38 linija: enum + temperature + leaf-priority). Sve ostalo je mjerenje, skille, boardovi, repo-mape, dokumentacija. Visok leverage, ali odnos je docs/tooling-težak.

3. **LOC vara — ne čitaj velike brojeve kao veliki kod.** bitlab-ai prikazuje +3961/−10630, ali **~13k churn-a su generisani eval-run artefakti** (a −10630 je njihovo arhiviranje, ne brisanje koda). Stvarni autorski churn ~1.339 linija / 18 fajlova, od čega je pola dokumentacija (repo-inventory ×2 jezika, repo-map).

4. **„Prazan četvrtak" je iluzija commit-boundary-ja.** Kalendarski git pokazuje čet 04.06 prazan, ali enum/temperature rad je sletio pet 00:52 (čet noć), a stord-04.06 sesija commit-ovana 07.06. Jedini stvarno mirniji dan je **pon 01.06** (1 bootstrap commit).

5. **Jak kontekst-switching, ali sa zajedničkom niti.** 31.05 (3 repoa prije podne), 03.06 (**4 repoa u istom minutu** za effort rollout), 07.06 (3 repoa uveče). Effort-level tema je provodna nit koja drži switch-eve smislenim, a ne raspršenim.

6. **Fokus = deklarisani prioritet (za headline).** Now inicijativa (grana `feat/ralph-categories-eval`) = categories acceptance — i **jeste zatvorena ove sedmice** (96,0% ≥ 95% cilj). Effort-standard je paralelna investicija, ne distrakcija.

7. **Effort → vrijeme (sanity).** L5 (effort-sistem) = klasa „sedmice–mjeseci", ali timeboxovan kroz ~3 sesije (02/03/07.06) — težina je u nefalsifikabilnom dizajn-prosuđivanju, ne u izvršenju. L3 (eval tuning, `/work`, brainstorm) = par dana–sedmica. L2 (cm-viewer) = 1–2 dana. L1 (cm-scraper) = ≤ dan.
