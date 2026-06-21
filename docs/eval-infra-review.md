# Review Sesije 2 — šta još treba popraviti

> **Status 2026-05-24 (after-action)**: tačke #1, #2, #3, #4, #9 adresirane u commit-ovima `7c94a16` (kritični #1+#2) i `637ebe5` (srednji+polish #3+#4+#9). Polish 5-11 ostale neadresirane — vidi `docs/eval-infra-changelog.md` Sesija 2b za detalje.

Pregled implementacije eval optimizacije + session-aware runner-a. Reference:
`EVAL_OPTIMIZACIJA.md` (originalni plan) i `docs/eval-infra-changelog.md`
(after-action izvještaj Sesije 1 i 2). Cilj ovog dokumenta: dati sljedećoj
instanci akcionabilan punch-list, ne ponovo opisivati šta je urađeno.

## Stanje

5 commit-a Sesije 2 push-ovano na `feat/ralph-categories-eval`, 149 pytest
prolaze + 1 skip (e2e Playwright). Plan EVAL_OPTIMIZACIJA Q1 (cache + sampler)
i Q2 (reactive 429 + proactive budget + cooperative PAUSE) je generalno
ispoštovan. TDD red→green je vidljiv iz commit history-a i `TDD RED faza`
komentara u test fajlovima.

## Šta je solidno, ne diraj

- **Kritična Sonnet review rupa popravljena** — `app/main.py:39-56` ima
  exception handler za oba SDK-a (openai.RateLimitError + anthropic.RateLimitError)
  → 429 sa `rate_limit:` u detail-u.
- **Cache invariant** pokriven kroz 25 unit + 7 integration testova
  (hash determinizam, invalidacija na prompt/tools/query change, ignor `tags`
  polja, NA skip, defensive na missing/corrupted).
- **Cache hit ne troši budget** — `test_runner_does_not_record_when_cache_hit`
  pokriva. Resume preko cache je realan win.
- **RateLimitDetected propagacija** — `client.py:32-34` specijalizuje 429,
  `runner.py:190` ga hvata posebno od generic Exception, exit kod 3 specifičan
  za rate-limit / budget.
- **Cooperative PAUSE marker** — jedan fajl sa opcionim `until=` linijom
  (per korisnikova preferenca, ne dva odvojena fajla). Runner ga piše, ralph.sh
  čita preko `wait_pause.py` helper-a, sa fallback estimate u ralph.sh ako
  runner ne stigne da piše marker.
- **Sampler determinizam** — seed=42, parent/leaf 50/50, manual/negative uvijek
  uključeno, rest fill dedup-uje po `id` (samo u rest fill grani, vidi rupu #4).

## Šta treba popraviti

### 1. KRITIČNO — JSONL inkrementalni append nije implementiran

Plan Sesije 2 Korak 1 je eksplicitno tražio:

> "Partial JSONL piše se inkrementalno (svaki entry odmah append), tako da
> resume produžava isti JSONL umjesto da pravi novi."

Stvarna implementacija (`evals/framework/reporter.py:12-20`,
`evals/framework/runner.py:209-214`):
- runner skuplja sve verdicte u `list[EvalVerdict]` kroz petlju
- na kraju zove `reporter.write_jsonl` koji koristi `time.strftime("%Y%m%d-%H%M%S")`
  i pravi NOVI fajl `<suite>-<label>-<NEW_TS>.jsonl`
- resume sa istim label-om → DRUGI fajl, ne nadovezuje se

**Posljedica**: 250-entry suite koji pauzira 3 puta (budget hit + 2 rate limita)
= 4 odvojena JSONL fajla. Faza 1 acceptance metrika "≥95% PASS kroz 250" se
ne računa bez manualnog merge-a. Ovo je tačno ona rupa koju je Sonnet review
i EVAL_OPTIMIZACIJA.md "Manje rupe" flagovao prije Sesije 2.

**Fix skica**:
- novi helper `reporter.append_verdict(run_dir, suite, label, verdict)` koji
  pravi/append-uje u stable path `<suite>-<label>.jsonl` (BEZ timestamp-a,
  ili sa timestamp-om iz checkpoint-a). Pisanje per-entry odmah nakon
  `verdicts.append(v)` u runner.py petlji.
- na clean completion runner može rename-ovati `<suite>-<label>.jsonl` u
  finalni `<suite>-<label>-<TS>.jsonl` (po želji za historical trace).
- HTML reporter može i dalje da piše na kraju (HTML je generated view nad
  JSONL-om).
- testovi: novi test koji pokriva "resume nadovezuje JSONL umjesto da pravi
  novi" — pokrene 5 entry-ja, prekine na index 2, resume sa istim label-om,
  verifikuje da je JSONL fajl jedan i sadrži 5 redova.

### 2. KRITIČNO (flaky test) — `_estimate_reset_epoch` čita pravi disk u testovima

`tests/integration/test_runner_writes_pause_marker.py` ne mock-uje
`_estimate_reset_epoch` niti override-uje `budget_dir`. Helper
(`evals/framework/runner.py:77-97`) čita `~/.cache/bitlab-ralph/pwr_calls.jsonl`.

Trenutno taj fajl ne postoji u test environment-u (jer Ralph nije pokrenut
još), pa testovi prolaze. Ali nakon prvog stvarnog Ralph run-a koji record-uje
pozive, log će postojati i ostati. Sljedeći test run:

- `_estimate_reset_epoch` čita najstariji unos
- ako je >5h u prošlosti (lako se desi), `oldest + 5h < now`
- `test_runner_pause_marker_until_is_valid_epoch:152` assert-uje
  `until_value > now - 60` → **fail**

**Fix**: u sva 3 testa u tom fajlu (`test_runner_writes_pause_marker_on_budget_exhausted`,
`test_runner_writes_pause_marker_on_rate_limit`,
`test_runner_pause_marker_until_is_valid_epoch`) eksplicitno prosljediti
`budget_dir=tmp_path / "budget"` u `runner.run_suite(...)`. Taj direktorij
test kreira ali ne puni, pa `_estimate_reset_epoch` fallback-uje na `now+5h`
(deterministički).

Provjeri da ovaj fix ne lomi `test_runner_writes_pause_marker_on_budget_exhausted`
— taj test već mock-uje `budget.count_calls_last_5h` na 60, ali to ne mijenja
ponašanje `_estimate_reset_epoch` koji čita disk direktno.

### 3. SREDNJI — sample mode CLI default vs AGENTS.md doc

`evals/framework/runner.py:289-294` ima `--mode` argparse sa `default="full"`.
`ralph/AGENTS.md:18` označava `--mode sample` kao "DEFAULT za iter".

Ralph mora eksplicitno passnuti `--mode sample` u svakoj iteraciji da bi
dobio sample mode. Doc to ne reflektuje.

**Fix** (jedan od dva, ne oba):
- (a) Promijeni argparse default na `"sample"`. Ralph automatski dobija
  brz signal, full mora eksplicitno preko `--mode full`.
- (b) Preformuliši AGENTS.md tabelu da kaže "preporučeno za iter" umjesto
  "DEFAULT". Manje invazivno ali ostavlja Ralph da redovno passuje flag.

Lično (a) je usklađenije sa namjerom plana (sample je default operativni mod,
full je acceptance verifikacija).

### 4. SREDNJI — sampler ne dedup-uje overlap manual + auto-gen tagova

`evals/framework/sampler.py:39-49`:
```python
manual = [e for e in entries if _has_tag(e, "manual") or _has_tag(e, "negative")]
auto_parent = [e for e in entries if _has_tag(e, "auto-gen") and _has_tag(e, "parent")]
auto_leaf = [e for e in entries if _has_tag(e, "auto-gen") and _has_tag(e, "leaf")]
selected = list(manual)
selected.extend(_safe_sample(rng, auto_parent, parent_quota))
selected.extend(_safe_sample(rng, auto_leaf, leaf_quota))
```

Ako entry ima istovremeno `manual` i `auto-gen` + `parent` tagove (mix),
biće u oba pool-a → može biti duplikat u `selected` listi PRIJE rest-fill
dedup grane (linije 53-57).

Trenutno suite fajlovi razdvajaju: `categories.jsonl` ima auto-gen + parent/leaf,
`categories_manual.jsonl` ima manual + negative. Pa praktično ne lomi nista.
Ali sampler je krhak ako neko spoji suite ili doda mix tag.

**Fix**: dodaj `seen: set[str] = {e["id"] for e in selected}` prije extend-ova,
filter `auto_parent`/`auto_leaf` da skipuju seen ID-eve. Plus dodaj unit test
sa entry koji ima i `manual` i `auto-gen` + `parent` tagove → mora biti samo
jednom u rezultatu.

## Manje krhkosti (ne hitnu, paket "polish")

5. `ralph/status.sh:23` koristi `pgrep -f "bash ralph/ralph.sh"`. Ne match-uje
   `./ralph/ralph.sh` ili `/usr/bin/bash ralph/ralph.sh`. Bolje: `pgrep -f "ralph/ralph.sh"`
   (bez prefiks-a `bash`).

6. `tests/integration/test_status_script.py:48-55`
   (`test_status_script_detects_ralph_not_running`) je praktično tautologija:
   `if "RADI\n" not in stdout.replace("NE RADI", ""): assert "NE RADI" in stdout`
   ne testira pouzdano. Bolje: forsiraj `Ralph NE RADI` u test environment-u
   (pgrep neće naći ništa), strict assert.

7. `app/agent.py:31` ima hardcoded `MAX_TOOL_ITERATIONS = 5`. Entry koji
   zahtjeva više od 5 tool poziva tihog stane sa potencijalno praznim reply-jem.
   Komentar to dokumentuje, OK za Fazu 1. U Fazi 2+ (multi-tool sekvence)
   premjesti u `app/config.settings`.

8. Nema CLI flag-a za cache flush. `--no-cache` samo bypass-uje lookup, ne briše
   fajlove. Da popraviš loš cached FAIL treba ručno `rm -rf evals/cache/`.
   Predlog: `--clear-cache` ili `--invalidate <entry_id>` flag.

9. `.gitignore:62` ima `# evals/runs/*.html` što je KOMENTAR (počinje sa `#`),
   ne pravilo. `docs/eval-infra-changelog.md:13` tvrdi da je `*.html` u
   ignore-u — nije. Ili uncomment-uj redu u `.gitignore` (ako odluka stoji
   da HTML ne ide u git), ili ispravi changelog. Trenutno HTML fajlovi
   nisu u `evals/runs/` pa nema pendinga, samo doc je netačan.

10. `evals/framework/reporter.py:76-77` `_escape` ne escapuje `"` karakter.
    Ako entry_id sadrži `"`, HTML atribut puca. Sitnica jer mi pišemo entry-je
    sami, ali defensive je 3 znaka.

11. `~/.cache/bitlab-ralph/pwr_calls.jsonl` raste zauvijek. `count_calls_last_5h`
    je defensive (skipuje stari), ali fajl ne rotira. Predlog: nakon učitavanja,
    runner može prepisati fajl samo sa unosima u trenutnom prozoru. Ne hitno.

## Šta je svjesno propušteno iz plana (ne diraj osim ako se eksplicitno traži)

- **Concurrent calls (Q1 #5)** — eksplicitno "Kasnije" u
  EVAL_OPTIMIZACIJA.md, korisno tek kad sesija nije bottleneck.
- **Prompt caching Anthropic put (Q1 #4)** — isto "Kasnije". PWR ne podržava.
- **Empirijska kalibracija MAX_CALLS=80** — open question u changelog-u,
  čeka prvi `[budget] paused...` log iz live run-a.

## Preporučeni redoslijed izvršenja

1. **Fix #2 prvo** (flaky test) — trivijalan, čisti se put da #1 testovi
   prolaze stabilno.
2. **Fix #1** (JSONL append) — najveći win, otključava Fazu 1 acceptance
   metric. Trebati će novi test (resume nadovezuje JSONL).
3. **Fix #3** (sample default) — trivijalna doc/code odluka.
4. **Fix #4** (sampler dedup) — trivijalan ako se odluči da sampler treba
   biti robusan; može se i samo dokumentovati neinvariant ako je
   "ne miješaj tagove u suite-u" prihvatljivo pravilo.

Sve ostalo (5-11) ide kao "polish" paket kada se ukaže prilika ili budu boljeli.

## Reference

- `EVAL_OPTIMIZACIJA.md` — originalni plan (Q1 + Q2 + Sonnet branch review).
- `docs/eval-infra-changelog.md` — after-action Sesije 1 i 2, sa propuštima.
- `feat/ralph-categories-eval-fix` (Sonnet branch) — više nije izvor; sve
  njegove ideje su prenesene u Korak 1, plus 429 handler rupa popravljena.
