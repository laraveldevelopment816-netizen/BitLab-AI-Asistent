# Eval infrastructure changelog

Hronološki dnevnik dorada eval frameworka tokom Faze 1 — šta je rađeno, zašto, šta je verify pokrivao i šta ostaje za sljedeću iteraciju. Cilj je da budući rad zna o čemu su prethodne sesije razmišljale.

## Sesija 1 (2026-05-24, popodne) — verdict cache + sample-first + status.sh + cleanup

### Kontekst pred početak

Ralph je odradio Faza 1 task 1-5 (auto-gen 250 entry-ja, oba toola, sistem prompt v1, negativni set sa 93.8% PASS) ali je iter 7 fail pattern analiza pokrenula full 250-entry suite i pojela cijelu PWR sesiju. Korisnik je dijelio sesiju sa drugim Claude radom i bio blokiran. Drugi Claude sa weba je prije toga ostavio `EVAL_OPTIMIZACIJA.md` sa pet nivoa optimizacije (verdict cache, tiered eval, prompt caching, concurrent calls, session-aware checkpointing) plus review nedovršenog `feat/ralph-categories-eval-fix` branch-a.

### Šta je urađeno

**Cleanup** (`evals/runs/`): obrisani pre-Ralph HTML/JSONL run-ovi (sve od `2026-05-23`) plus moji adhoc smoke run-ovi. `evals/runs/` skinut iz `.gitignore` ali `*.html` i `archives/` ostali u ignore-u jer je HTML samo generated pregled iz `reporter.write_html()`, dok JSONL je SSOT (~10KB po run-u) koji se sad commit-uje za PR audit. `evals/cache/` dodan u `.gitignore` (regenerabilan disk store).

**`ralph/status.sh`**: bash dashboard koji u jednom komandu ispiše da li Ralph radi (preko `pgrep`), trenutnu iter iz najnovijeg log-a, posljednjih osam redova log-a, posljednja tri commit-a, broj Now i Done task-ova iz `IMPLEMENTATION_PLAN.md`, top Now task naslov, i statistiku posljednjeg eval JSONL-a (total/PASS/FAIL/WARN/rate). Boje za quick scan (zeleno = RADI, žuto = NE RADI / STOP marker). Cilj je da korisnik ne mora otvarati tri terminala da bi znao stanje.

**`PROMPT_build.md` STATUS blok**: Faza 7 sad obavezuje Ralph da prije exit-a ispiše jedan red u stdout u formatu `STATUS | iter=N | task="..." | commit=sha7 | eval=X/Y (rate%) | next="..."`. Korisnik kroz `tail -F` log-a vidi progres po iteraciji bez parsing-a tijela.

**`evals/framework/cache.py`** — verdict cache: SHA-256 hash kombinacije `SYSTEM_PROMPT_V1` + JSON `ALL_TOOLS_ANTHROPIC` + normalizovan entry (id + query + history + expect, ne tags jer su tags metapodatak). Disk store `evals/cache/<hash>.json`. `cache_get` defensive (vraća `None` za missing dir, missing fajl, ili corrupted JSON). `cache_put` skipuje NA verdicte (entry ne testira ništa, kešovanje nije win) ali kešira PASS, FAIL i WARN — uključujući FAIL jer je uzrok često determinističan (loš prompt / tool / dispatch) pa ponovni pokušaj ne treba trošiti sesiju.

**`evals/framework/sampler.py`** — stratified sampling: manual/negative entry-ji uvijek prolaze (kritičan signal, mala grupa), parent/leaf 50/50 split iz auto-gen-a, deterministički seed=42, fallback na random fill ako jedna grupa nema dovoljno entry-ja. Cilj: sample od 30 stratificiranih + manual 16 = 46 poziva po iter umjesto full 250.

**`evals/framework/runner.py`** dopune: `--mode sample|full` (default full), `--no-cache` (bypass cache layer), `--cache-stats` (dry, samo statistika). Cache lookup prije svakog `_run_entry`, put nakon. Sample mode poziva `sampler.stratified_sample` prije limita.

**`tests/unit/test_eval_cache.py`** — 25 unit testova kroz dva commit-a: hash determinizam, invalidacija na prompt/tools/query change, ignorisanje tags polja, get/put roundtrip za PASS/FAIL, NA skip, stats sa corrupted fajlovima, unicode u query, sampler edge cases (prazan input, target_size=0, untagged entries, parent/leaf balance, manual coverage).

**`tests/integration/test_eval_runner_cache.py`** — 7 integration testova: JSONL/HTML write, `--limit 0`/`--limit N`, cache hit drugog run-a sa istim signature-om = 0 novih HTTP poziva, `--no-cache` disable, promjena `_get_signature` invalidira cache, `--mode sample` uzima 30 iz 100, `--fail-fast` staje na prvom FAIL-u.

**`tests/integration/test_status_script.py`** — 4 integration testa: `subprocess.run("bash ralph/status.sh")` exit 0, output sadrži sve sekcije (proces, log, commits, plan, eval), detektuje "NE RADI", citira top Now task.

**`tests/unit/test_ralph_prompt.py`** — 6 regression guard testova za `PROMPT_build.md` (STATUS blok, 999.9 guardrail, "NE pravi novu granu") i `AGENTS.md` (`--mode sample` doc, `status.sh` u tabeli).

### Šta je propušteno (kritika korisnika nakon ove sesije)

Ono što sam ja predstavio kao "sample uštedi 82% troška" je istina samo za broj eval entry-ja po iter-u, ne za stvarni budžet PWR sesije. Realnost: 46 entries × prosječno 3 Claude poziva po entry-ju (tool dispatch loop) = 130-150 LLM poziva samo iz eval runner-a, plus svake Ralph iteracije Claude proces puno tokena pojede čitanjem PROMPT-a, IMPLEMENTATION_PLAN, code grep-om, edit-ovima. Sample mode čini iteraciju **bržom**, ne **jeftinijom**. Plus, kad rate limit lupi, Ralph padne sa "Not logged in", restartom kreće isti task od nule — sav rad iteracije se baca. Resume state je bio Sonnet 4.6 web prijedlog u `feat/ralph-categories-eval-fix` koji sam ja odbacio jer "cache + sample je dovoljno". Nije.

Plus, način rada — pisao sam kod gdje sam trebao pitati. Arhitekturne odluke (kakav budget tracker, gdje state, pauza vs exit) nisu stilske odluke. Ovo je naučeno za sesiju 2.

## Sesija 2 (2026-05-24, predveče) — resume + budget tracker + cooperative pause

### Kontekst pred početak

Sesija 1 je riješila brzinu (sample) i preglednost (status.sh, STATUS blok), ali ne i blokadu sesije. Cilj sesije 2: Ralph radi do ~65% sesije pa pauzira; kad rate limit ipak lupi, ne baca rad iteracije; korisnik može cooperative paušalno kontrolisati kad Ralph spava (npr. kad počne svoj posao u drugom Claude terminalu).

### Plan (potvrđen sa korisnikom)

Tri inkrementalna commit-a, TDD pristup, sa pauzom nakon svakog za review:

**Korak 1 — FastAPI 429 handler + eval runner checkpoint + `--resume` flag**:
- `app/main.py` dobija `@app.exception_handler(openai.RateLimitError)` i isto za `anthropic.RateLimitError` → vraća 429 response sa `{"detail": "rate_limit: ..."}` u body-ju. Trenutno FastAPI guta ove kao 500, eval client ih ne prepoznaje.
- Novi modul `evals/framework/errors.py` sa `class RateLimitDetected(Exception)`.
- `evals/framework/client.py` hvataj 429 iz HTTP odgovora, diže `RateLimitDetected`.
- `evals/framework/runner.py` hvataj `RateLimitDetected` u `_run_entry`, snima `evals/runs/<label>.checkpoint.json` sa `{"next_index": N, "entries_processed": N}`, prekida petlju, exit kod 3.
- `--resume <label>` flag čita checkpoint pri pokretanju i kreće od `next_index`. Cleanup checkpoint-a na uspješan completion.
- Partial JSONL piše se inkrementalno (svaki entry odmah append), tako da resume produžava isti JSONL umjesto da pravi novi.

**Korak 2 — Budget tracker (empirijski call count)**:
- Novi modul `evals/framework/budget.py` sa:
  - `record_call(cache_dir, timestamp)` — append u `~/.cache/bitlab-ralph/pwr_calls.jsonl`.
  - `count_calls_last_5h(now)` — sumira pozive u rolling 5h prozoru.
  - `should_pause(now, max_calls=80, threshold=0.65)` — vrati True ako count > 80 × 0.65 = 52 poziva.
- `runner.run_suite` prije svakog `_run_entry` provjeri `should_pause`; ako True → snima checkpoint, exit kod 3.
- Početni `MAX_CALLS=80` je konzervativna procjena (kalibruj na osnovu prvih nekoliko rate-limit hit-ova).

**Korak 3 — Cooperative PAUSE + ralph.sh sleep logika**:
- `ralph.sh` while petlja detektuje exit kod 3 iz `claude --print`.
- Ako kod 3 → piše `ralph/PAUSED_UNTIL_<epoch_timestamp>` sa procjenom reseta (najstariji unos u call log + 5h).
- Sleep do tog timestamp-a (ne busy poll) pa nastavi.
- Plus cooperative marker `ralph/PAUSE` (bez timestamp-a) — Ralph završi tekuću iter pa čeka da korisnik `rm ralph/PAUSE` ručno.
- STOP marker ostaje za hard exit.

### Verify procedura

Svaki korak ima TDD ciklus: testovi prvo (red), implementacija (green), pa backpressure (`ruff format && ruff check && mypy app/ evals/framework/ && pytest -q`). Commit ide tek nakon green. Push ide na trenutnu feature granu `feat/ralph-categories-eval`. Sve PR-ovi prema `claude/tdd-zero-base` (memorija `tdd-zero-base-branch-workflow`).

### Otvorena pitanja za kasnije

- **Empirijski MAX_CALLS = 80 — kalibracija**: prva 1-2 rate-limit-a će reći šta je stvarni ceiling, pa tweakujemo. Trenutni 80 je nazgodičan konzervativan default.
- **PWR vraća tokens u usage?**: ako da, token-based budget je precizniji od broja poziva. Provjeriti u prvoj sesiji pod nadzorom.
- **Prompt caching (Q1 #4 iz EVAL_OPTIMIZACIJA)**: 90% off na cached portion za Anthropic put. Nepotrebno za PWR (paušal). Implementirati ako i kad treba puno više Anthropic eval-a.
- **Concurrent calls (Q1 #5)**: 4× brže za 4× pool, ali ne štedi kvotu. Tek kad sesija nije bottleneck.

## Reference

- `EVAL_OPTIMIZACIJA.md` u root-u — pun plan optimizacije sa pet nivoa Q1 + dvije strategije Q2 + review Sonnet branch-a.
- `feat/ralph-categories-eval-fix` (branch) — Sonnet 4.6 web prijedlog za checkpoint/resume; sadrži ideje koje su prenesene u Korak 1 plus rupu (FastAPI gutaš 429 jer nema handler-a) koja se popravlja TDD-om u Sesiji 2.
- `git show 3d4bc87:app/agent.py` — stari `_run_pwr` referenca za OpenAI tools shape derivaciju.
- Memorije: `llm-backend-pwr-imperative`, `tdd-zero-base-branch-workflow`, `anthropic-budget-mock-tests`, `feedback-test-case-invariant`, `feedback-one-fix-at-a-time`.
