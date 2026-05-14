---
date: 2026-05-14
branch: main
participants:
  - Ivan Kukic (Kule)
  - Claude Code (voice consumer)
slug: 2026-05-14-bitlab-konsolidacija-i-planiranje
---

# Brainstorm — bitLab konsolidacija i planiranje

## Agenda

1. Srediti dokumentaciju bitLaba.
2. Napraviti listu tačaka koje treba završiti na bitLabu.
3. Konsolidacija grana — `staging` je divergirala od `main`; postoji još
   jedna `nnn-feature-nnn` grana koju treba uporediti i konsolidovati.
   Cilj: čist `main` + `staging`.
4. Lista pitanja za gospodina Đuru + lista otvorenih pitanja koja treba
   riješiti za potpuno siguran produkcijski sistem.
5. Otvorena pitanja sa Google Drive-a → prebaciti u issues / napraviti
   task listu tih pitanja.

## Log

<!-- running notes, hronološki -->

### Tačka 5 — Google Drive otvorena pitanja (pribilježeno, obrada kasnije)

- Korisnik je dodao `docs/Otvorena pitanja sa Google Drive-a.md` (23.6 KB) u repo.
- Treba ga konsolidovati → pretvoriti u actionable stavke (issues / task lista).
- Status: zabilježeno, obrada kad dođemo na tačku 5.

### Tačka 3 — konsolidacija git grana (u toku)

Snimak stanja grana (2026-05-14):

- `main` @ `0d3d4cc` — sinhronizovan sa `origin/main`.
- `staging` @ `572043e` — sinhronizovan sa `origin/staging`.
- `feature/ai-search-brand-category-improvements` @ `091040e` — SAMO lokalna, nema remote.
- `feature/n8n-deploy` @ `d485b0a` — prati `origin/feature/n8n-deploy`.

**main ↔ staging** (main +4, staging +1):
- Staging-ov "jedini" commit `572043e` ima IDENTIČAN patch-id (`a4eec2b3…`) kao
  `7125d10` na main → duplikat, sadržaj je već na main.
- Net `git diff main staging` = samo `public/widget.js` (−35/+28) → staging je
  efektivno SAMO iza main-a, nema stvarnog unikatnog rada.
- Zaključak: staging se može poravnati na main; nema pravog merge konflikta.

**feature/ai-search-brand-category-improvements** (main +5, feature +0):
- 0 unikatnih commita → grana je u potpunosti merge-ovana u main. Stale.
- Kandidat za brisanje (`git branch -d …`, lokalno; nema remote).

**feature/n8n-deploy** (main +8, feature +1):
- 1 stvaran unmerged commit `d485b0a` "n8n: subpath deploy + Gmail OAuth uputstvo".
- Sadržaj: README, `deploy/n8n-*.service`, `docs/operations/gmail-oauth-setup.md` (197),
  `docs/operations/n8n-odluka.md` (229), `docs/operations/n8n-setup.md`,
  `n8n/email-autoreply.json` — 485 insertions, stvaran rad (deploy config + docs).
- Kontekst: n8n je up na serveru ali blokiran DNS-om (memory `project_n8n_setup_state`).

**Nezakomitovano na `main` (snimak na početku sesije, van uže konsolidacije):**
- Modifikovano: `.env.example`, `app/agent.py`, `app/config.py`, `app/server/dashboard.py`.
- Untracked: `CLAUDE.md`, `.env.openclaw`, `--fix-missing` (izgleda kao slučajno
  kreiran fajl od pogrešno otkucane komande — provjeriti/obrisati).

**Otvorena pitanja za odluku (tačka 3):**
1. `staging`: reset --hard na main + force-with-lease push (destruktivno, shared
   remote), ILI merge main → staging (ostavlja duplikat commit u historiji)?
2. `feature/ai-search-brand-category-improvements`: obrisati (merged, stale)?
3. `feature/n8n-deploy`: merge-ovati `d485b0a` u main sad (docs/config su aditivni)
   ili držati granu otvorenu dok n8n ne bude live?

**Pojašnjenje — kako je `staging` divergirao** (na pitanje korisnika):
- Tačka razdvajanja: `58a8a69` (Merge feature/ai-search…). Tu su `main` i `staging` poravnati.
- Poslije toga je "voice.html: sakrij mikrofon" fix commit-ovan DVA PUTA:
  - na `staging`-u kao `572043e` (roditelj `58a8a69`),
  - na `main`-u kao `7125d10` (roditelj `a51f0a2` = "Merge staging → main").
  - Isti sadržaj (isti patch-id `a4eec2b3…`), različit SHA → git ih vidi kao divergenciju.
- `main` je zatim nastavio sa `efae235` + `0d3d4cc` (widget commiti); `staging` stao na `572043e`.
- Suština: `staging` nema nijedan red koda koji `main` već nema — "unikatni" commit je duplikat.

**Pojašnjenje — `feature/ai-search-brand-category-improvements`** (na pitanje korisnika):
- Čisto lokalna grana (nema remote). Commit `091040e` je POTVRĐENO predak `main`-a
  (`git merge-base --is-ancestor` = true). Sav sadržaj je u `main` (merged kroz `58a8a69`).
- Brisanje grane uklanja samo zaostali label — nula izgubljenog rada.

### Analiza nezakomitovanih promjena na `main` — OpenClaw integracija (na pitanje korisnika)

**Šta je:** prvi pass integracije sa **OpenClaw gateway-em** — cilj da agent ide
kroz lokalni Claude CLI *subscription* umjesto metered Anthropic API-ja
(`ANTHROPIC_API_KEY`). Motivacija: trošak (flat subscription vs per-token).

**Stanje po fajlovima:**
- `app/config.py` (+19/−3): nove postavke `use_openclaw` (default `False`),
  `openclaw_base_url`, `openclaw_api_key`, `openclaw_model`. Validator za
  `anthropic_api_key` više ne zahtijeva ključ kad je `use_openclaw=True`.
  Odvojeno: dodat `opus_model = claude-opus-4-7` u alias mapu.
- `app/agent.py` (+54): nova `_run_agent_openclaw()` — **chat-only passthrough**
  preko `httpx` na OpenAI-compatible `/v1/chat/completions`. `run_agent()` dobio
  rani `if settings.use_openclaw:` granu prije Anthropic puta.
- `app/server/dashboard.py` (+1) i `.env.example` (+1): Opus 4.7 u cost tabelu /
  kao opcioni override — **odvojena tema od OpenClaw-a**.
- `.env.openclaw` (untracked): template + razvojna bilješka.
- `--fix-missing` (untracked): sadržaj `{}` — slučajno kreiran junk fajl, obrisati.
- `CLAUDE.md` (untracked): projektne smjernice, zaseban commit (nije dio feature-a).

**Ključna korekcija — NIJE "kompletno novi feature", nepotpun je:**
- Radi samo **chat-only** put, iza flag-a koji je default ugašen.
- **Tool-use** (pretraga proizvoda, eskalacija) NE ide kroz OpenClaw — a to je
  produkcijski put (potvrđeno komentarom u `config.py`).
- Razvojna bilješka u `.env.openclaw` to i kaže: *"NOT YET WIRED… substantial
  refactor (~2-4h)… keep direct Anthropic API as default until refactor is done."*
- Dakle: dva nesaglasna stanja — kod ima djelimičan passthrough, a bilješka
  opisuje veći refactor (`anthropic.Anthropic` → `openai.OpenAI`).

**⚠️ Sigurnost:** `.env.openclaw` sadrži stvaran ključ (`OPENCLAW_API_KEY=cfcc8bc3…`).
Trenutno untracked (nije commitovan) — dobro — ali NE smije se commitovati.
Dodati `.env.openclaw` u `.gitignore`.

**Bundling:** Opus-4.7 izmjene (`opus_model`, cost tabela, `.env.example`) su
zasebna, manja tema umiješana u isti blob — kandidat za odvojen commit.

### Provjera namjere — opis "watchdog za log-analizu" vs. kod (na pitanje korisnika)

Korisnik je opisao osnovnu ideju OpenClaw fičera kao: nezavisni personalni agent /
*posebna aplikacija* koja analizira logove na admin strani, traži nelogičnosti
(da li ljudi dobijaju prave odgovore), kontroliše greške u realnom vremenu.

**Ne mogu to potvrditi — kod NE odgovara tom opisu.** Dokaz (grep cijelog repa):
- "openclaw" se pojavljuje samo na 3 mjesta: `app/config.py`, `app/agent.py`,
  `.env.openclaw`. Nema zasebne aplikacije, nema `openclaw/` modula.
- Grep za `analiz|nelogičn|watchdog|inconsisten|monitor.*log` po `*.py` →
  **0 rezultata**. Nema log-analize, QA-provjere, watchdog koda nigdje.

**Šta kod STVARNO radi:** `_run_agent_openclaw()` živi UNUTAR `run_agent()` —
funkcije koja generiše agentove odgovore korisnicima. To je transport swap: isti
posao (odgovori korisniku), drugi backend (gateway sa Claude CLI subscription
umjesto Anthropic SDK). Motiv: trošak.

**Šta NE postoji u kodu:** log-analiza, admin-side komponenta, detekcija
nelogičnosti / kvaliteta odgovora, zasebna aplikacija, real-time monitoring grešaka.

**Zaključak / otvoreno pitanje:** vizija ("watchdog") i kod su se razišli. Ili je
watchdog zasebna, neimplementirana ideja, ili je OpenClaw rad odlutao od
prvobitnog cilja — ne može se iz koda utvrditi koje, korisnik treba razriješiti.
Moguće da je prvobitna ideja zapisana u `docs/Otvorena pitanja sa Google Drive-a.md`
(tačka 5) — mjesto za cross-check.

### Korisnikovo pojašnjenje — šta je OpenClaw zapravo (mijenja sliku)

Korisnik je pojasnio: **OpenClaw je potpuno zasebna git aplikacija na njegovom
računaru** — njegov lični AI agent. Koristi Claude Opus 4.7, šalje dnevne daily
briefove, ima "personality i karakter" — razgovor kroz njega djeluje kao razgovor
sa čovjekom.

Namjera za `bitlab-ai-asistent`: dati OpenClaw-u **"entrance"** u aplikaciju da:
- može da je **nadgleda / kontroliše** (logovi, kvalitet odgovora, greške u real-time);
- kod **eskalacije** eventualno **zamijeni čovjeka** (zbog personality-ja).

**Reconciliation sa ranijom analizom:**
- Vizija "watchdog" NIJE nestala — OpenClaw je stvaran, samo živi u DRUGOM repo-u.
  Ranija formulacija "vizija i kod su se razišli" je nepotpuna: tačnije je da je u
  `bitlab-ai-asistent` kodiran tek **most/bridge**, i to samo jedna polovina.
- Vizija ima dva smjera:
  - **(A) bitlab → OpenClaw** — bitlab koristi OpenClaw kao mozak/glas (personality,
    human-like eskalacija). Trenutni `_run_agent_openclaw` passthrough je **prvi
    korak ka ovome**, chat-only.
  - **(B) OpenClaw → bitlab** — OpenClaw nadgleda/kontroliše bitlab, čita logove.
    **Nula koda za ovo.** To je "entrance" koji korisnik opisuje.
- Korekcija ranije tvrdnje: Opus-4.7 izmjene (`opus_model`, cost tabela) su nazvane
  "odvojena tema" — vjerovatno PREuvjereno. OpenClaw koristi Opus 4.7, pa su te
  izmjene mehanički zaseban code-path ali najvjerovatnije ista inicijativa.

**Otvoreno pitanje:** dovršiti smjer (A) ili krenuti na (B)? Trenutni kod ne radi
ono što korisnik primarno želi (nadzor/kontrola = smjer B).

> Sačuvano u memoriju: `project_openclaw_personal_agent.md`.

### PRIJEDLOG — plan konsolidacije gita (na zahtjev korisnika; NE izvršavati sad)

Korisnik traži plan, ne izvršenje ("to nećemo raditi sada"). Ciljna struktura:
`main` (čist) • `staging` (poravnat na main) • `feature/openclaw-integration` (novo,
parkiran rad + status) • `feature/n8n-deploy` (postojeći, parkiran).

**Redoslijed je bitan** — OpenClaw rad je u radnom stablu `main`-a; mora prvo sići
sa stabla da bi ostale operacije bile čiste.

**Korak 1 — Sačuvati OpenClaw rad na vlastitoj grani (PRVO).**
- Sa (prljavog) `main`-a: `git checkout -b feature/openclaw-integration` (uncommitted
  izmjene idu sa stablom na novu granu).
- Dodati `.env.openclaw` u `.gitignore` (sadrži stvaran ključ — NIKAD ne commitovati).
- Commitovati SAMO OpenClaw fajlove: `app/agent.py`, `app/config.py`,
  `app/server/dashboard.py`, `.env.example`, `.gitignore`.
- Pod-odluka: Opus-4.7 izmjene (`opus_model`, cost tabela, `.env.example` red) —
  preporuka: izdvojiti u zaseban mali `feat:` commit na `main` (aditivne, samostalno
  korisne); alternativa: ostaviti bundlovane na grani.

**Korak 2 — STATUS.md na OpenClaw grani.**
- Sadržaj već postoji u ovom logu: vizija (OpenClaw = zaseban personal agent, smjerovi
  A/B), šta trenutno radi (chat-only passthrough iza flag-a), šta NE radi (tool-use
  ~2-4h, cijeli smjer B). Uključiti i dev-bilješku iz `.env.openclaw` (fajl ide u gitignore).
- Lokacija: `docs/openclaw/STATUS.md` (prijedlog).

**Korak 3 — Očistiti radno stablo `main`-a.**
- `git checkout main` → tracked stablo je sad čisto (OpenClaw delta commitovana na grani).
- `rm ./--fix-missing` (junk, sadržaj `{}`).
- Commitovati preostale untracked: `CLAUDE.md`, `docs/Otvorena pitanja sa Google
  Drive-a.md`, `docs/brainstorm/` — kao `docs:`/`chore:` commit(e) na `main`.

**Korak 4 — Poravnati `staging` na `main`.**
- `staging`-ov jedini "unikatni" commit je potvrđen duplikat → bezvrijedan.
- Preporuka: `git checkout staging && git reset --hard main && git push --force-with-lease origin staging`.
  ⚠️ Destruktivno + force-push na shared remote → po workflow pravilima: jedna komanda
  po turi, eksplicitno odobrenje, verifikovati served. Tek kad se ovo izvršava.
- Alternativa (bez force-push): `git merge main` u staging — ostavlja duplikat commit
  u historiji, messy. Ne preporučujem.

**Korak 5 — Stare feature grane.**
- `feature/ai-search-brand-category-improvements` — potpuno merged, local-only, stale
  → `git branch -d …` (siguran delete jer je merged).
- `feature/n8n-deploy` — 1 stvaran unmerged commit, n8n blokiran DNS-om (memory
  `project_n8n_setup_state`) → držati otvorenu, ne merge-ovati sad.

**Rezultat:** `main` čist i kanonski • `staging` = `main` • `feature/openclaw-integration`
(parkiran rad + STATUS.md) • `feature/n8n-deploy` (parkiran) • ai-search grana obrisana.

**Otvorene pod-odluke za korisnika:** (1) Opus-4.7 split na main ili bundle na grani;
(2) staging `reset --hard` vs `merge`; (3) potvrda brisanja ai-search grane;
(4) n8n grana — držati ili merge-ovati.

**Refinement (korisnikov prijedlog):** umjesto "branch off prljavog `main`-a pa
checkout nazad", obrnuti redoslijed Koraka 1/3 — prvo commitovati na `main` ono što
pripada main-u (`CLAUDE.md`, docs), pa tek onda `git checkout -b feature/openclaw-…`
za OpenClaw kod. `git checkout -b` prenosi i staged i unstaged izmjene → ekvivalentan
rezultat, malo čišće (doc commiti se prave dok si stvarno na `main`-u). Kritičan
uslov za OBA puta: staging EKSPLICITNO po imenu fajla, nikad `git add -A` (da
OpenClaw kod ne procuri na `main` i da se `.env.openclaw` sa ključem nikad ne
stage-uje). — Čeka pojašnjenje: šta je "LPPO"?

### `--fix-missing` — definitivna provjera (na pitanje korisnika)

- **Namjena/funkcija: nikakva.** Sadržaj: `{}` (2 bajta). Nije referenciran NIGDJE
  u repo-u (0 grep pogodaka). Nikad nije bio u git istoriji (`git log --all
  --full-history` prazan). Nije u `.gitignore` — čist untracked junk.
- Kreiran 2026-05-08 21:47 (poklapa se sa LIVE test pripremom za 2026-05-08).
- Porijeklo (zaključak, ne 100% potvrda): `--fix-missing` je poznat CLI flag (npr.
  `apt-get … --fix-missing`); najvjerovatnije je flag slučajno završio kao ime
  fajla / redirect target neke komande koja je upisala `{}`.
- **Akcija:** bezbjedno obrisati — `rm -- ./--fix-missing` (ništa se ne lomi:
  untracked, nereferenciran). Komanda stavljena na /dictate panel.

### Stanje radnog stabla — kategorizacija za commit (na pitanje korisnika)

Na grani `main`. `--fix-missing` je OBRISAN (korisnik izvršio `rm` sa panela). ✅

Preostalo uncommitted, kategorizovano:

**Za `main` (3 fajla, čisti — cijeli fajl ide na main):**
1. `CLAUDE.md` — projektne smjernice
2. `docs/Otvorena pitanja sa Google Drive-a.md` — Drive pitanja (tačka 5)
3. `docs/brainstorm/2026-05-14-bitlab-konsolidacija-i-planiranje/log.md` — ovaj log

**Za `feature/openclaw-integration` (NE na main):**
- `app/agent.py` — 100% OpenClaw (nema Opus sadržaja)
- `app/config.py`, `app/server/dashboard.py`, `.env.example` — OpenClaw + Opus-4.7
  izmiješani; Opus dio je još otvorena pod-odluka (split na main preko `git add -p`
  ili bundle na grani)

**Nikad ne commitovati:**
- `.env.openclaw` — sadrži ključ → `.gitignore`

### Commit — 3 main fajla, lokalno (korisnik odobrio: "ja commitujem", bez push)

Korisnik odobrio: ja pravim commite **pojedinačno**, **lokalno na `main`**, **bez
`git push`** ("nemoj još da ih pušaš").

Tri pojedinačna `docs:` commita na `main`:
1. `CLAUDE.md` → `docs: add CLAUDE.md project guidelines`
2. `docs/Otvorena pitanja sa Google Drive-a.md` → `docs: add open questions imported from Google Drive`
3. `docs/brainstorm/2026-05-14-…/log.md` → `docs: add brainstorm session log (git konsolidacija i planiranje)`

OpenClaw fajlovi (`app/*`, `.env.example`, `.env.openclaw`) NISU dirani — ostaju
uncommitted za `feature/openclaw-integration`. Nema push-a. SHA-ovi: `git log`.
(Napomena: ovaj log se i dalje dopunjava nakon commita #3 → biće opet "modified".)
