---
date: 2026-06-07
branch: feat/ralph-categories-eval
participants: [Ivan, Claude (voice)]
slug: 2026-06-07-plan-effort-burndown
---

# Brainstorm — Action plan, effort estimate & burndown chart

## Tema i prioriteti

Cilj sesije, po prioritetu:

1. **Akcioni plan** — kreirati / urediti akcioni plan za projekat.
2. **Procjena efforta** — procijeniti težinu zadataka iz tog plana.
3. **Burndown chart** — izgraditi burndown do kraja projekta (vezano za zaseban / treći repozitorijum, ali želimo i to).

---

## Transkript

### Turn 1 — Ivan
> Kod tema današnje sesije, kreiranje akcijskog plana, te procjenjivanje težine zadataka, te izgradnja burndown charts-a do kraja projekta. Kako se učiniti?
>
> Prioritet 1: akcioni plan. Prioritet 2: procjena efforta tih zadataka. Prioritet 3: burndown chart (vezan za treći repozitorijum, ali želim i to).

### Turn 1 — Claude
Slug potvrđen, folder + log skeleton kreiran. Krećemo od prioriteta 1 (akcioni plan).

### Turn 2 — Claude (nalaz stanja)
Provjerio `docs/plans/akcioni-plan.md` + `STATUS.md`. Ključni nalaz koji mijenja premisu:

- **Akcioni plan već postoji** (ažuriran 2026-05-29), nije ga potrebno praviti od nule.
- **Now inicijativa `evfx`** (popravka eval regresije → acceptance) je **faktički završena**:
  acceptance pun 250 = **96,0%**, prag ≥95% oboren. Sve kartice (`acpt`, `lfpr`, `tght`,
  `dsmp`, `rvpr`, `frtl`, `setp`, `i17r`, `fz00`) su u **Done**. Todo i Doing su **prazni**.
- **Effort je već primijenjen** na Done karticama (`effort:N pct:PP` oznake postoje).
- **Next** čeka: Faza 2 (RAG `search_products`, `fza2`), Faza 3 (cross-reference, `fza3`).

Posljedica za 3 prioriteta:
1. **Akcioni plan** = zatvori `evfx` (→ Completed), promovisati **Fazu 2** (RAG proizvodi)
   iz Next u Now, pa je `decompose-initiative` skillom razbiti u taske.
2. **Effort** = svaku novu Faza-2 tasku ocijeni `estimate-effort-level` (4-dim A/B/J/V →
   `effort:N pct:PP`) — isti model kao postojeće Done kartice.
3. **Burndown** = agregiraj `pct` težine (Done = spaljeno, Todo = preostalo) kroz vrijeme do
   kraja projekta. "Treći repozitorijum" gdje burndown živi — **otvoreno pitanje** (TBD).

Predloženo: krećemo redom od prioriteta 1.

### Turn 3 — Ivan (puni zahtjev, recovered iz queue)
Slaže se s nalazom. Ali ključne korekcije i dopune:

- **Korekcija meni:** "konstantno govoriš da je akcioni plan završen, ali nije". Rad (eval, 96%)
  jest gotov; **plan kao dokument NIJE** — nije detaljan, ima otvorenih tačaka, nema arhive.
- Ima **mnogo stavki za izdiktirati** koje nisu u planu (npr. *Anthropic prompt caching* = daleki Later).
- Predlog: napraviti **"action to-do list" file vezan za akcioni plan** za sve takve stavke.
- **Arhiva:** proći planove/docs (ima ih 4–5 strana), skroz završeno → `docs/archives/`
  (folder ne postoji — kreirati). Usput srediti i ostalu dokumentaciju.
- **Nemamo skill** za akcioni-plan lifecycle. Želi skill par onome za STATUS
  (`analyze`/`synchronize-status` koji prebacuje kartice u Done) — ali za plan: kad inicijativa
  potpuno završi → prebaci + **napomena** (sad napomene fale).
- Otvorene tačke se **ne preskaču** — sve napisano je validno. Npr. Ralph autonomni loop: zaključeno
  da nije nužan uz forsiran tool, ali **šta s loop-om** — možda ga prenamijeniti za druge svrhe
  (vuče nova pitanja).
- Faza 2 spec (`specs/products.md`) — radila ga Ralph petlja; nije siguran je li validan.
- Workaround ideja (jer nema skill-a): postojeći plan → **deprecated**, napraviti novi, prebaciti iz starog.
- **Zadatak meni:** "smisli pa mi javi". On u međuvremenu pregleda repo.

### Turn 3 — Claude (nalazi iz repoa + prijedlog pristupa)

**Nalazi (provjereno `find`/`ls`/`wc`):**
- `docs/archives/` **ne postoji** → kreirati.
- Root ima **12 .md** (~1440 lin). Kandidati za arhivu: `EVAL_REGRESIJA_iter17.md` (dijagnoza gotova,
  `i17r` Done), `EVAL_OPTIMIZACIJA.md`, eventualno `repo-inventory-*.md` / `repo-map*.md` ako su stale.
  Živo (ne dirati): `CLAUDE.md`, `PLAN.md`, `README.md`, `STATUS.md`, `STATUS-HUMAN.md`.
- `specs/`: `categories.md`, `cross-reference.md`, **`products.md` = samo 11 linija** → tanak stub
  (potvrđuje sumnju); mora se proširiti **prije** decompose Faze 2.
- `ralph/` živ: `ralph.sh`, `ralph-plan.sh`, `IMPLEMENTATION_PLAN.md`, `status.sh` … → otvoreno pitanje prenamjene.
- `docs/`: `PROMPT-BEST-PRACTICES.md` (živo), `eval-infra-changelog.md`, `eval-infra-review.md`, `fb-funnel-progress.md`.

**Prijedlog pristupa — refactor, NE deprecate cijelog plana (gubi se trag/kontekst):**

1. **Arhiva:** kreiraj `docs/archives/`, pa dokument-po-dokument (ti potvrđuješ) skroz završeno seli tamo.
   Plan i root ostaju vitki. (Obrazac: `archive-status` skill već radi `docs/archives/status-archive-YYYY-MM.md`.)
2. **Plan refactor (ne deprecate):** `evfx` Now → Completed + napomena (96%, datum); otvorene tačke
   (Ralph loop prenamjena, rezolucija "forsiran tool vs loop") **zapisane kao napomene/odluke**, ne brisane;
   promovisati **Faza 2 → Now**.
3. **Backlog inbox:** novi `docs/plans/backlog.md` — sirovi inbox za diktirane stavke koje nisu zrele za
   Now/Next (npr. prompt caching = far-Later, loop reuse). Ti diktiraš stavku-po-stavku, ja rutiram
   (Now/Next/Later/backlog). To je traženi "action to-do vezan za plan".
4. **Faza 2 priprema:** proširi `specs/products.md` (sad 11 lin) → tek onda decompose → STATUS taske →
   effort (4-dim) → burndown.
5. **Plan-lifecycle skill (zasebno, u `bitlab-standards`):** par `analyze-plan`/`synchronize-plan`
   STATUS-paru — Now/Next/Later→Completed + napomene + arhiviranje. Rješava "nemamo skill". Ne blokira 1–4.

**Redoslijed:** ti diktiraš stavke (3) dok ja pripremam arhivu (1) → plan refactor (2) → Faza 2 spec (4) → skill (5).
Čeka se odluka korisnika od čega prvo.

### Turn 4 — Ivan (board OK + korekcije + start arhive)
"Board je perfektno." Korekcije i odluke:

- **Prioritet 1 badge "u toku" — ne dirati.**
- **Arhiva NIJE vezana za plan.** Arhiva = **outdated projektni MD dokumenti** (iz roota, `docs/`,
  `specs/` placeholderi) — zapažanja, izvještaji koje je sam kreirao kroz projekat. Primjer:
  iteracija 17 koja je pala (`EVAL_REGRESIJA_iter17`) → arhiva. **Nije vezano za kartice/planove.**
- **Reorg koraka u plan-refactoru:** dio "dokument-po-dokument selimo; plan i root ostaju vitki"
  pripada koraku **1 (arhiva)**, ne planu. Obrazac **`archive-status` skill** izdvoji kao **tačku 6**
  (vidjeti kako ga unaprijediti).
- **Redoslijed rada:** prvo arhiva (1), pa **2 i 3 zajedno** (plan refactor + backlog inbox).
- **Sad odmah:** kreiraj `docs/archives/`; prvi dokument u arhivu = **`STATUS-HUMAN.md`**.

### Turn 4 — Claude (izvršeno)
- ✓ `docs/archives/` kreiran.
- ✓ `git mv STATUS-HUMAN.md docs/archives/` — rename staged (istorija sačuvana), **nije commitano**.
- Razdvojio koncept: **arhiva = projektna dokumentacija** (root/docs/specs), odvojeno od plana/kartica.
- Board reorganizovan: korak 1 = arhiva projektne dokumentacije (✓ započeto); `archive-status`
  unapređenje = nova **tačka 6**; tok 1 → 2+3 → 4 → 5 → 6.
- Pitao korisnika koji dokument sljedeći ide u arhivu (diktira jedan-po-jedan).

### Turn 5 — Arhiviranje (running log)
Korisnik diktira dokumente za arhivu jedan-po-jedan; svaki `git mv` u `docs/archives/` (rename staged, bez commita):

1. `STATUS-HUMAN.md` ✓
2. `EVAL_REGRESIJA_iter17.md` ✓ (iter17 dijagnoza — završeno, `i17r` Done)

Preostali kandidati (nepotvrđeni): `EVAL_OPTIMIZACIJA.md`, `repo-inventory-{en,me}.md`, `repo-map{,-simplified}.md`, možda `RESTORE.md`. Živo: `PLAN.md`, `README.md`, `STATUS.md`, `CLAUDE.md`.

### Turn 6 — Ivan (Ralph loop priča → review/lessons + notes)
Ispričao punu Ralph-loop sagu i tražio destilaciju u dokumente u `docs/plans/`:

- **Narativ:** krenuli od nule; korisnik napravio autonomnu petlju da sama piše prompt. Radila super —
  sama dodavala pravila, pokretala testove, digla ~56% → 84% (iter8). Onda dodala `category_overview` →
  pad. Pauzirali → skontali da fali **forsiran tool calling**. Dodali treći tool `respond_to_user` (+ enum,
  temp) → preko 95%. "Loop nam je korak-po-korak ukazao na problem, ali fix je tražio tehničko znanje koje
  dotad nije vidio."
- **Zahtjevi:** (1) dokument **review/findings/lesson-learned** — dvodijelan (autonomna petlja | ručni dio),
  **link na `EVAL_REGRESIJA_iter17.md`** (arhiva). (2) dokument **notes** — inbox za napomene/zanimljivosti.
- **Format (kritično):** za 3–5 sek pri otvaranju mora biti kristalno jasno šta je u dokumentu i gdje stoji —
  jedna stvar po dokumentu, "ne šest stvari odjednom". "Nemoj da je lijepo" (= bez ukrasa, samo jasno).
  (Poklapa se s `feedback_laser_focus_docs`.)
- **Akcioni plan ne dirati** sad (Now "završen ali ima detalja").

### Turn 6 — Claude (izvršeno)
Pročitao `docs/archives/EVAL_REGRESIJA_iter17.md` za tačne brojeve, pa kreirao:
- ✓ `docs/plans/lessons-learned.md` — **L1 = Ralph loop regresija**, Poenta na vrhu + Dio 1 (autonomno) /
  Dio 2 (ručni fix) + putanja 56→84→79→96 + link na iter17 arhivu.
- ✓ `docs/plans/notes.md` — sirovi inbox, cross-link na lessons.
Tačni brojevi iz iter17: iter8 **84,4%** (179/212) → iter17 **79,2%** (168/212), neto **−11**; svih
**29/29 regresija = apstinencija toola** (halucinacija kataloga); fix forsiran tool → **96,0%**.
Akcioni plan netaknut. Nije commitano.

### Turn 7 — Infra incident (people-first, van teme sesije)
Korisnik prijavio da mu dug diktat puca uz "Slanje propalo" i izgubio dosta izdiktiranog; tražio rekonstrukciju.
Dijagnoza (read-only nad people-first; patch NE radim — nije caller-repo, ide kroz dev sesiju people-first):

- "Slanje propalo" = `public/dictate.html:757/798` (`setStatus('Slanje propalo: '...)`) — fail na `POST /api/dictate`.
- Docker log dokaz: `POST /api/stt 200 OK` → `POST /api/dictate 422 Unprocessable Entity` (jedini 422 u logu).
- Uzrok: `DictateRequest.text` ima `max_length=4000` (`app/main.py:434`); Whisper STT nema limit → dug
  transkript prođe STT ali padne na dictate (422) **prije** `logger.info("dictate queued")`.
- **Sadržaj nepovratan:** `/api/stt` audio čita u memoriju i ne čuva na disk; STT ne logira transkript;
  dictate 422 prije upisa u queue. Nema traga → ne rekonstruišem, ne izmišljam.
- Workaround (korisniku): diktiraj u dijelovima < 4000 znakova.
- Fix (predan kao `cmd.sh` task za people-first dev sesiju): (1) frontend recovery — vrati tekst u
  `#textInput` pri fail-u; (2) brojač + upozorenje pred limit; (3) podići `max_length` / chunk-ovati.

### Turn 8 — Ivan (sirovi capture — nastavak teme; NIŠTA ne smije ispasti)
Nastavljamo. Zahtjevi (raspoređujem u board / backlog / lessons / notes; akcioni-plan.md Now NE diram):

**Board — novi prioriteti:**
- **Prioritet 4 — Evaluation Framework** (eval infra kao zaseban tok).
- **Prioritet 5 — Ralph petlja: self-correcting / self-building software.** Analiziraj NAŠU Ralph petlju i
  **nazovi je pravim imenom po industrijskom standardu** — to ime ide u **CV** (klasifikovati profesionalno).

**Iz `EVAL_OPTIMIZACIJA.md` (root) → stavke u backlog/todo** (pa dokument arhivirati na kraju):
1. **Prompt caching** — postoji opcija; suzi na jednu rečenicu. Obavezna tačka da završimo, ali **Later (later)**.
2. **Paralelno izvršavanje testova** — konkurentno, da brže izvršimo više evalova paralelno. (Super, brzo izvršivo.)
3. **Self-aware session limit** — korisno, dodati.
4. **Error handling — popraviti** — nešto urađeno, nešto ostalo. Konkretno: framework prijavljuje
   *false positive* na *network error* → nisu sve greške obrađene kako treba; provjeriti ili je implementacija loša.
5. **Bug: kombinacije flagova** — više flagova zajedno (npr. `--limit ... --what ...`) nije testirano /
   nije test-driven; ne hvataju se svi flagovi kad ih ima više. (Eval framework bug.)

**Lessons-learned (nova lekcija, već IMPLEMENTIRANO):**
- **Caching po prompt-hash-u (resume loop-a).** Ako loop pukne na npr. 50. pozivu, ne kreće od nule kroz svih
  20/50 poziva — nastavi od **zadnjeg uspješno keširanog** (npr. odmah na 21), ne troši tokene/vrijeme.
  Kad se prompt promijeni → keš se **automatski invalidira**. Vrlo korisno; zabilježiti kao lekciju.

**TODO (iz mog ranijeg prijedloga):** prompt caching (gore #1). Provjeriti obradu grešaka (false positive /
network error) — nije sve pokriveno.

**Na kraju:** kad sve prebacim, `EVAL_OPTIMIZACIJA.md` → `docs/archives/`.

### Turn 9 — Claude (raspoređeno; EVAL_OPTIMIZACIJA pročitan i mapiran)
Provjereno: **verdict cache JE implementiran** (`evals/cache/` stotine `.json`, `--no-cache`/`--cache-stats`,
auto-invalidacija — `ralph/AGENTS.md:64`). Ralph mehanika: eval-gated, "failing eval → minimum dodaj → PASS",
backpressure (ruff+mypy+pytest) prije commita, čist kontekst po iteraciji, sam committa + `touch ralph/STOP`.

Urađeno:
- ✓ `docs/plans/backlog.md` — kreiran; Evaluation Framework (P4) stavke + P5 + Later (prompt caching, 1 rečenica).
  Svaka stavka ima izvor (EVAL_OPT Q#/review).
- ✓ `lessons-learned.md` += **L2 — verdict cache po prompt-hashu** (resume bez troška, auto-invalidacija; dokaz).
- ✓ `notes.md` += napomena: kontradikcija `--mode sample` (AGENTS.md:64 / EVAL_OPT Q1#2) vs L1 (sample laže).
- ✓ board: dodati **P4 Evaluation Framework** + **P5 Ralph petlja (CV naziv)**; naslov "Prioriteti 2–5".
- **Klasifikacija Ralph (prijedlog za CV):** *autonomous, eval-gated self-improving LLM agent loop* ("Ralph"
  tehnika) — coding agent iterativno piše/testira/commita protiv automated eval harness-a, sa verdict cache +
  checkpoint/resume + CI-gated commit. Kategorija: agentic AI / autonomous software engineering.

- ✓ Arhivirano: `EVAL_OPTIMIZACIJA.md` → `docs/archives/` (sad 3 dokumenta u arhivi).

Preostalo: potvrda klasifikacije Ralph (za CV), burndown "treći repo" pitanje.

### Turn 10 — Ivan (linkovi + backlog struktura + caching gore)
- **Linkovi ka MD dokumentima svuda** gdje se pominju — na većini ima, ali fali: u `notes.md` (gdje se
  pominju `EVAL_OPTIMIZACIJA.md` i `ralph/AGENTS.md`) → dodati linkove.
- **Backlog struktura kao lessons** (L1/L2 sa `---` linijama) → "Prioritet 1, Prioritet 2…" sa `---` separatorima.
- **Prompt caching: Later → Prioritet 1** ("to nam je sad u planu now/next/later, sredi to").

### Turn 10 — Claude (izvršeno)
- ✓ `backlog.md` reorganizovan: **P1 = Prompt caching** (dignut iz Later), **P2 = Evaluation Framework**,
  **P3 = Ralph klasifikacija**, sa `---` linijama između; dodati linkovi na `app/agent.py`, `app/main.py`,
  `EVAL_OPTIMIZACIJA.md` (arhiva), `ralph/AGENTS.md`, `STATUS.md`, `lessons-learned.md`, `notes.md`.
  Napomena u zaglavlju: backlog-prioriteti = redoslijed izvršavanja (≠ board-prioriteti 1–5).
- ✓ `notes.md`: linkovi na `ralph/AGENTS.md`, `EVAL_OPTIMIZACIJA.md` (arhiva), `L1`.
- ✓ `lessons-learned.md` L2: `ralph/AGENTS.md` referenca → link.
- Otvoreno (pitam): da li prompt caching upisati i u formalni `akcioni-plan.md` (Now/Next/Later) — taj
  dokument dosad NISAM dirao po ranijoj instrukciji; backlog P1 je zasad jedino mjesto.

### Turn 11 — Ivan (root cleanup + objedinjavanje; snimak OPET pukao)
Puno zahtjeva (sirovi capture; razvrstano na JASNO / NEJASNO):

**JASNO:**
1. **Objediniti 4 root fajla u 2:** `repo-map.md` + `repo-map-simplified.md` → jedan **po folderima**
   ("repo-inventory-folder-group"); `repo-inventory-en.md` + `repo-inventory-me.md` → jedan **po komponentama**
   ("repo-inventory-component-group"). Imena "tako nekako". **Staviti u plan/`docs/plans/`.**
   **Regenerisati SVJEŽ sadržaj** — stari je outdated jer smo sve ispremještali (arhiva, novi docs/plans).
2. **Spojiti `PLAN.md` + `RESTORE.md`** u jedan → `docs/plans/`. (`PLAN.md` = prvi korak, repo od nule prije
   Ralph petlje; `RESTORE.md` = kako vratiti tu staru varijantu ako zatreba.)
3. **Prompt caching → DOLJE** (niži prioritet) u backlogu. *(obrat od turn 10 — sad jasno dolje)*
4. **Cilj: očistiti root → ostaje "bukvalno 6" fajlova.**

**NEJASNO (pitati):**
- **Backlog "final"** — "now/next/later, final, tako se zove final"? Preimenovanje backloga? now/next/later struktura?
- **"Work" eval-acceptance nalaz** — "zašto preostalih 7 od 15 i dalje pada, koje kategorije i zašto, enum/temp".
  Gdje je taj nalaz (koji fajl)? Ili da ja napravim analizu padova? "napravi to pa da vidimo".
- Kojih tačno **6 fajlova** ostaje u rootu.

**Akcija (Claude):** caching → dolje (odmah); čitam PLAN/RESTORE + tražim work nalaz; spajanja predlažem pa pokažem.

### Turn 12 — Claude (lociran work nalaz; PLAN/RESTORE pročitani)
- ✓ Caching premješten **dolje** u backlogu (P1 Eval FW, P2 Ralph, Later: caching).
- ✓ **Work nalaz lociran:** `docs/work/2026-05-29-eval-acceptance/nalaz-fail-set-enum-temp.md` (+ `board.html`).
  Sažetak: 14/23 PASS; 8 leaf-kolizija riješeno (izbor alata OK). Preostalih **7/15 pada NIJE leaf/parent**:
  4× tačan alat / pogrešan-ali-validan ID (`cat-leaf-186/274/329` + "Sony"=brend), 3× apstinencija na
  maglovitim jednorječnim ("Ventilatori" ×2 s različitim ID = nedobitno; "Dodaci" pregeneričko).
  **Ključ: enum garantuje validan ID, ne tačan.** Preporuka nalaza: ne juriti promptom → Faza 2 / known-limit.
- ✓ **PLAN.md / RESTORE.md pročitani** (materijal za spoj): PLAN = TDD zero-base reset (repo od nule, sve u
  `bck/`, eval-driven); RESTORE = recept za povratak originalne app iz `bck/`. Tematski par → spoj smislen.
- Fragmenti "1." / "Ovo je" — nepotpun diktat; čeka se dovršenje + šta s work nalazom (lekcija? link? premjestiti?).

### Turn 13 — Ivan (pojašnjenje: finalni plan + filozofija)
- **Backlog → "Finalni akcioni plan" (Now/Next/Later).** To je prioritet 1.
- **Work nalaz (preostalih 7)** = prvo da vidimo (Now); uz njega u zagradi **"(analizirano — nije prompt-fixing)"**.
- **Prompt caching dolje** — potvrđeno (već urađeno).
- **PLAN+RESTORE spoj → gore pri vrhu**, jer ćemo *po toj poslovnoj logici izvlačiti stvari iz `bck/`* da
  ništa ne promakne.
- **Filozofija (ključno):** app je **ZAVRŠENA** — nema novih fičara, sve postoji u `bck/`; treba ih samo
  izvući i popraviti da rade u **produkciji**.

### Turn 13 — Claude (izvršeno)
- ✓ `docs/plans/baseline-i-restore.md` — spoj PLAN+RESTORE; svrha na vrhu (izvuci iz `bck/` → produkcija),
  Dio 1 zero-base reset / Dio 2 restore recept.
- ✓ `docs/plans/backlog.md` → **Finalni akcioni plan (Now/Next/Later)**:
  - **Now:** izvlačenje iz `bck/` → produkcija (link na baseline-i-restore); preostalih 7 padova
    *(analizirano — nije prompt-fixing → Faza 2/known-limit)* (link na work nalaz).
  - **Next:** Faza 2 RAG (`specs/products.md` tanak); Evaluation Framework (detalji).
  - **Later:** prompt caching; Ralph klasifikacija.
- Sljedeće (najavljeno): arhivirati `PLAN.md`/`RESTORE.md` iz roota + fix linkova (`STATUS.md`/`akcioni-plan.md`
  referenciraju `PLAN.md`); objediniti 4× repo-inventory/map → 2 (svjež sadržaj, skeniranjem repoa).

### Turn 14 — Ivan (ISPRAVKA: backlog ≠ plan)
**Pogriješio sam: spojio backlog i akcioni-plan u jedno.** Ispravka:
- **Backlog ostaje backlog** (memorija/inbox) — vrati kako je bio prije turn-13 promjene. Eval Framework,
  Ralph, prompt caching tu čekaju jer **nisu prioritet sad**.
- **Now/Next/Later je ZASEBAN** (akcioni-plan) — **radimo ga ZAJEDNO**, ne ja sam.
- Od now/next/later koji sam napravio: **Now (prve 2-3 tačke) DOBRE**; **Next NIJE** — Faza 2, Ralph loop,
  Eval FW "nisu nam prioritet sad".

### Turn 14 — Claude (revert + razdvajanje)
- ✓ `backlog.md` vraćen na inbox (P1 Eval FW / P2 Ralph / Later caching) — naslov "Memorija / inbox, NIJE plan".
- **Sačuvane DOBRE Now tačke** (za zajednički now/next/later, da se ne izgube):
  1. Izvlačenje poslovne logike iz `bck/` → produkcija (po `baseline-i-restore.md`).
  2. Preostalih 7/15 acceptance padova *(analizirano — nije prompt-fixing → Faza 2 / known-limit)*.
- Next se NE finalizuje sam — čeka zajednički rad.
- Zadržano (nije bila greška): `baseline-i-restore.md`, arhiva `PLAN.md`/`RESTORE.md`, ref-fix.

### Turn 15 — Ivan (backlog prioriteti = board prioriteti)
- Backlog P1 ne može biti Evaluation Framework — **backlog prioriteti moraju pratiti BOARD (P1–P5)**.
  Eval FW = **P4**, Ralph = **P5** (kao board).
- **Backlog P1 = board P1 = Akcioni plan (Now/Next/Later).** Pod njim kandidati od kojih pravimo plan:
  izvlačenje iz `bck/`, preostali padovi (analizirano), prompt caching, + NOVO: **prompt sanitization**,
  **prompt injection (zaštita)**.
- Potvrdio dobro: `baseline-i-restore.md` (bck → produkcija restore). Samo backlog ispraviti.
- Bojazan da je nešto "iskeširalo" (vidio staru verziju). "Probaj pa se javi, pitaj ako ne znaš."

### Turn 15 — Claude (backlog preslikava board P1–P5)
- ✓ `backlog.md`: P1 Akcioni plan (+ kandidati: bck-restore, padovi, caching, **sanitization**, **injection**),
  P2 Procjena efforta, P3 Burndown, P4 Evaluation Framework, P5 Ralph — svaki označen `· board PN`.
- Otvoreno (pitam): (a) **prompt caching** pod P1-kandidati ili dolje (Later)? (b) jesam li dobro uhvatio
  **sanitization/injection** kao nove stavke? (c) treba li P2/P3 u backlogu ili samo na boardu (sad ih ima).

### Turn 16 — Ivan (STOP: previše promjena; vrati na zadnji dobar korak)
Frustriran — previše velikih/nejasnih promjena u zadnja 2-3 koraka; ne radim inkrementalno ("vrati jedan").
- **Ralph CV klasifikacija je IZGUBLJENA** ("autonomni LLM agent self-improving…") — bila referenca na
  lessons-learned ali tamo NIJE upisana → slomljeno. Vratiti je eksplicitno.
- Eval Framework i Ralph = **zasebne komponente** (razviti), ne checkbox-pretrpane liste; checkbox-i nebitni.
- effort/burndown nisu prioritet (ali mogu stajati); važnije popisati Eval FW + Ralph.
- repo-inventory/map objedinjavanje JOŠ nije urađeno (čeka).
- **Instrukcija:** prođi log, nađi zadnji DOBAR korak, vrati backlog na to; pa će diktirati jedno-po-jedno.

### Turn 16 — Claude (revert na zadnji dobar korak)
- Identifikovan zadnji dobar backlog = **turn 9 struktura**: P4 Evaluation Framework + P5 Ralph petlja
  (zasebne komponente) + Later prompt caching.
- ✓ `backlog.md` vraćen na to + **Ralph klasifikacija upisana eksplicitno** ("autonomous, eval-gated
  self-improving LLM agent loop", agentic AI / autonomno SW inženjerstvo). Bullet liste umjesto checkbox-a.
- Maknuto (bilo prevelika promjena): P1 Akcioni-plan-u-backlogu, P2 effort, P3 burndown sekcije.
- Sačuvano da se ne izgubi (Ivanove nove stavke iz turn 15, NISU ubačene — čekaju diktat): **prompt
  sanitization**, **prompt injection zaštita**.
- Ne dirano: board (P1–P5 OK), `baseline-i-restore.md`.

### Turn 17 — Ivan (diktat 1/n: caching = Faza 1)
- **Prompt caching → Faza 1** (prvo na redu), van Later. "90% uštede", iz EVAL_OPTIMIZACIJA, cache_control polje.
- Nejasno: "dodaj to za sad kao fazu jedan **od 40 dana**" — rok? trajanje? → pitam.

### Turn 17 — Claude
- ✓ `backlog.md`: dodata **Faza 1 — Prompt caching** na vrh (90% ušteda, `cache_control`, izvor EVAL_OPT Q1 #4);
  uklonjena Later sekcija. Eval FW (P4) / Ralph (P5) netaknuti. Inkrementalno, ništa drugo.

### Turn 18 — Ivan (diktat 2/n; "40 dana" bilo slučajno)
Dodati u backlog, redoslijedom:
- **Izvlačenje poslovne logike iz `bck/` → produkcija** (po baseline-restore + repo-inventory).
- **Preostalih 7/15 acceptance padova** (analizirano, nije prompt-fixing, mapira na Faza 2 / known-limit; vidi work nalaz).
- **Faza 2 — RAG `search_products`** (pravi RAG, bira po query; `specs/products.md` tanak → proširiti prije dekompoza).
- "to je to za sada".

### Turn 18 — Claude
- ✓ `backlog.md`: dodate 3 sekcije između Faza 1 (caching) i P4 — Izvlačenje iz `bck/`, Preostalih 7/15 padova,
  Faza 2 RAG. Redoslijed kako je diktirano. Eval FW/Ralph netaknuti.

### Turn 19 — Ivan (struktura: kartice u Prioritetu 1)
- **Ukloni "Faza 1/Faza 2" nazive.** Sve stavke (caching, izvlačenje, padovi, RAG) → **kartice unutar Prioriteta 1**.
- **Prioritet 1 = "Akcioni plan (Now/Next/Later) · board P1 u toku".**
- **Redoslijed kartica** (sa korekcijom — RAG na vrh): 1. RAG `search_products`, 2. Izvlačenje iz `bck/`,
  3. Preostali padovi 7/15, 4. Prompt caching, 5. Prompt sanitization (čišćenje/validacija ulaza),
  6. Prompt injection. "S tim bismo završili tačku 1."
- "napravi pa ću pogledati kad završiš".

### Turn 19 — Claude
- ✓ `backlog.md` reorganizovan: **Prioritet 1 — Akcioni plan (Now/Next/Later) · board P1, u toku** sa 6
  numerisanih kartica tim redoslijedom (RAG → bck-izvlačenje → padovi → caching → sanitization → injection).
  "Faza" nazivi uklonjeni. P4 Evaluation Framework / P5 Ralph (sa CV klasifikacijom) netaknuti ispod.

### Turn 20 — Ivan (Prioritet 1 završen; dodaj P2/P3)
- Prioritet 1 za sad **završen**.
- Dodati: **Prioritet 2 = Estimate effort** (procjena efforta), **Prioritet 3 = Burndown chart**.

### Turn 20 — Claude
- ✓ `backlog.md`: dodati **P2 Procjena efforta** + **P3 Burndown chart** (board P2/P3) između P1 i P4.
  Backlog sad kompletno preslikava board: P1 (6 kartica) · P2 · P3 · P4 Eval FW · P5 Ralph.

### Turn 21 — Ivan (veliki diktat: P1 dopune + novi P6)
**Dodati u P1 (Akcioni plan):**
- **FAQ** (frequently asked questions).
- **Edge case-ovi** za sve: kategorije, proizvodi, baza znanja, `respond_to_user`. Pregledati cijeli `bck/` prompt.
- **Prompt injection + eval test** — agent ne smije odati ključeve; primjeri iz `bck/` prompta → ekstraktovati.
- **UI po JSON šemi** (zaboravljeni dio) — agent vraća JSON podatke po šemi, layout se renderuje na widgetu (sad agent generiše UI po specifikaciji).
**Premješteno:** prompt sanitization P1 → **P6**.
**Novi Prioritet 6 — dodavanje ostalih tool-ova iz `bck/`:** n8n email automatizacija; voice chat; sinhronizacija
baze (cron → BitLab baza + WebShop, vektorski indeks dnevno); autentifikacija na dashboard (sad HTML); dashboard
debug/poboljšanja; search-more proizvoda (cijeli katalog kroz agenta); + prompt sanitization.

**KONFUZNO (pitam, NISAM dodao):**
- **Kategorije klikabilne na widgetu** (sad čipovi, treba klikabilne + ikonice) — rekao "faza 2", ali P2 = effort. Gdje?
- **"Pokrenuti sve eval testove" + "baza testova" + "eval za search_products"** — P1 (uz edge cases) ili P4 (Eval Framework)?

### Turn 21 — Claude
- ✓ `backlog.md`: P1 prošireno na 8 kartica (RAG, izvlačenje, padovi, caching, **injection+eval**, **FAQ**,
  **edge cases**, **UI JSON šema**); sanitization izmješten u **novi P6** sa bck tool-ovima. P2/P3/P4/P5 netaknuti.
- 2 konfuzne stavke NISU dodate — čekaju razjašnjenje (vidi say).

### Turn 22 — Ivan (P1 kartice 9/10 + objedini repo-inventory 4→2)
- Obje konfuzne → **Prioritet 1**: kategorije klikabilne na widgetu (kartica 9), eval testovi (kartica 10).
- **Objediniti 4 repo fajla → 2**, staviti u `docs/plans/` (po komponentama + po folderima).

### Turn 22 — Claude (izvršeno)
- ✓ P1 kartice 9 (kategorije klikabilne) + 10 (eval testovi) dodate.
- ✓ Repo-inventory **4 → 2** (BS verzije zadržane, EN duplikati u arhivu):
  - `repo-inventory-me.md` → `docs/plans/repo-inventory-component-group.md` (po komponentama)
  - `repo-map-simplified.md` → `docs/plans/repo-inventory-folder-group.md` (po folderima, statusi)
  - `repo-inventory-en.md`, `repo-map.md` → `docs/archives/`
  - oba osvježena (delta): root očišćen na 3 `.md`, `docs/plans/` proširen, `docs/archives/` uvršten.
- **Root sad: `CLAUDE.md`, `README.md`, `STATUS.md`** (+ `pyproject.toml`, `scan.sh`, `repo-scan.md` ne-md) = cilj "6 fajlova".

### Turn 23 — Ivan (finale P1 + commit/push)
- Spoj kartica **7 (edge cases) + 10 (eval testovi)** → edge case-ove nalazimo KROZ eval testove, za sve toolove
  (`category_overview`, `search_products`, baza znanja, FAQ, `respond_to_user`); pokreni sve uklj. regresiju;
  pregledati `bck/` prompt.
- Nova **kartica 8** = novi set testova za sve toolove/kategorije ("sito i rešeto").
- Renumeracija: UI po JSON šemi 8→9, kategorije klikabilne 9→10.
- "Zaključujemo sesiju. **Možeš komitati i pušati.**"

### Turn 23 — Claude
- ✓ P1 kartice preuređene (7 spoj edge+eval za sve toolove, 8 novi set testova, 9 UI-JSON, 10 klikabilne).
- Slijedi: `git add -A` + commit + push (grana `feat/ralph-categories-eval`).
- ✓ **Commit `2817146`** (17 fajlova, 777+/32−), **push OK** na `feat/ralph-categories-eval`. Git rename istorija
  sačuvana za sve premještene fajlove. **Sesija zaključena.**

---

## Zaključak sesije (2026-06-07/08)

Sesija je počela kao "napravi akcioni plan + effort + burndown", a prerasla u **temeljno čišćenje i restrukturiranje dokumentacije**. Tri pouke:

1. **Periodično čišćenje repoa je neophodno — svakih 2-3 dana, najviše sedmicu.** Radi-pa-spoji divergencije zamrse repo brže nego što se očekuje; root je bio nepregledan (12 `.md`), sad je 3. Bez redovnog čišćenja postaje nemoguće pratiti.

2. **Tight coupling → loose coupling za reuse.** Eval Framework i Ralph petlja razvijani su ZAJEDNO (feature: auto-nastavljanje preko checkpoint/resume) pa su sad tight-coupled — trebaju oba. Sljedeći cilj: dekaplovati ih u **loose-coupled, reusable komponente** koje se mogu koristiti na drugom projektu (novi prompt + Now/Next/Later, model već u `bitlab-standards`). Procjena: ~90% je već reusable, fali dekaplovanje.

3. **Prvi siguran signal štedi od ponavljanja svega.** 96% acceptance je bio taj signal — dokaz da smo na pravom putu i da ne moramo ispočetka. Akcioni plan + rani pouzdan signal = ne radiš dvaput (a ovo je već drugi put da se nešto pravi iznova).

**Fun fact:** sesija o *sređivanju* plana sama je prošla kroz ~10 reorganizacija backloga — caching gore↔dole, "faze"↔"prioriteti", spajanje pa razdvajanje plana i backloga. Živi dokaz pouke #1: dok smo čistili, čišćenje je pokazalo koliko se brzo zamrsi.
