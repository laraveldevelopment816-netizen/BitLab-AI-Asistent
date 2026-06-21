# Predlog — optimizacija PWR eval poziva + session-aware runner

Sažetak razgovora 2026-05-24. Pokriva dva pitanja:
1. Kako smanjiti broj realnih PWR poziva kroz Faza 1 acceptance (250-entry suite).
2. Kako runner napraviti svjestan PWR session limita prije nego što lupi.

Plus review branch-a `feat/ralph-categories-eval-fix` (Sonnet 4.6 web) koji
adresira dio (2) reaktivno.

---

## Stanje (referenca)

- **Faza 1, iter 6**: SYSTEM_PROMPT_V1 single source (`app/agent.py:38-60`),
  oba tool-a (`category_overview`, `search_products`) u oba runnera, eval set
  250 + 16 manual.
- **Posljednji live eval (PWR)**: manual 16 → 93.8%, sanity 20 → 95%.
- **Now task u `ralph/IMPLEMENTATION_PLAN.md:7`**: fail-pattern analiza full 250 +
  manual 16. Acceptance ≥95% PASS.

---

## Q1 — Smanjenje broja realnih poziva (250-entry full run)

Pet nivoa, od najjeftinijeg ka najskupljem. Preporuka: implementirati #1 i #2,
ostalo opcionalno.

### 1. Verdict cache po `(entry_id, prompt_hash, tools_hash)`

**Win**: 80-90% štednja od druge iteracije.

- Disk store `evals/cache/<hash>.json`.
- Hash = sha256(`SYSTEM_PROMPT_V1` + `ALL_TOOLS_ANTHROPIC` JSON + `entry`).
- Re-run preskoči entry ako cached verdict postoji za isti hash.
- Promijeniš prompt → svi hash-evi se mijenjaju → invalidiraš sve.
- Popraviš jedan entry tekst → invalidiraš samo taj.
- Mijenja se samo `evals/framework/runner.py` (lookup prije `_run_entry`).

**Procjena**: ~1h rada.

### 2. Tiered eval (sample-first)

**Win**: svaki iter ti je ~18% sadašnjeg troška.

- Default eval per Ralph iteraciji: manual 16 + stratificirani sample 30 iz 250 ≈ 46 poziva.
- Full 250 samo kad sample ≥95%.
- Stratifikacija: balanced kroz parent/leaf/brand/edge — ne random.
- Sample seed deterministički da je reproducibilan.

**Procjena**: ~30 min rada (mali helper za sampling + nova `--mode sample|full`).

### 3. Stratifikacija samog sample-a

Već uračunato u #2 — sample od 30 random je nestabilan signal; sample od 30
stratificiranih kroz `(level, has_brand, edge_case)` daje pouzdanu fail-pattern detekciju.

### 4. Prompt caching

**Win Anthropic**: 90% off na cached portion (sistem + tools = ~2-3k tokena × 250).

- Anthropic put: `cache_control: {"type":"ephemeral"}` na zadnjem tool bloku
  u `app/agent.py:121`.
- PWR put: vjerovatno **ne podržava** (OpenAI shape nema `cache_control`).
  Vrijedi probati kroz `extra_body` — ako PWR ignoriše, samo nije win za PWR.

**Procjena**: ~15 min Anthropic, neizvjesno za PWR.

### 5. Concurrent calls

**Win**: 4× brže ali **isti session budget** (ne štedi kvotu, samo vrijeme).

- PWR ima fiksan pool browser tab-ova (provjeriti konfiguraciju, default 1-4).
- Ako pool=4 → `asyncio.gather` u runner-u, 4 paralelna `_run_entry`.

**Procjena**: ~1h rada. Korisno tek kad sesija nije bottleneck.

---

## Q2 — Self-aware session limit

PWR ne objavljuje tačan Pro/Max limit; Anthropic ga ne dokumentuje za pretplate.
Dvije strategije, hibrid je najbolji.

### A) Reactive — parse 429 + checkpoint

- Wrap PWR call u try/except na 429 / quota response.
- Snimi `evals/runs/<label>.checkpoint.json` sa "do indexa N urađeno".
- Exit sa porukom "resume sa `--checkpoint <path>` u HH:MM".
- Pair sa #1 cache → resume je besplatan (cache hituje sve već urađene).

**Sonnet 4.6 je ovo već implementirao na `feat/ralph-categories-eval-fix` — vidi review niže.**

### B) Proactive — lokalni token brojač sa sliding window

- Append `(timestamp, tokens_in+out)` u `~/.cache/pwr_usage.jsonl` poslije svakog poziva.
- Sumiraj posljednjih 5h prije svakog poziva (Pro/Max je rolling window).
- Empirijski nauči ceiling: kad lupiš limit pri X tokena, postavi `BUDGET = X * 0.9`.
- Stop runner kad sum > BUDGET, ispiši ETA reseta najstarijeg unosa.

**Procjena**: ~2h rada + nekoliko ciklusa kalibracije.

### Hibridni preporučen redoslijed

1. **Sad**: reaktivni 429 checkpoint (Sonnet branch + popravke iz review-a niže).
2. **Sljedeće**: verdict cache (Q1 #1) — radi vise nego brojač jer eliminiše ponovne pozive.
3. **Kasnije**: proaktivni budget tracker (Q2-B) kad si empirijski naučio gdje ti je ceiling.

---

## Review — `feat/ralph-categories-eval-fix` (commit d180970)

Sonnet 4.6 web je odradio minimalno reaktivno rješenje Q2-A. Diff:
`evals/framework/{client,runner}.py` + `ralph/AGENTS.md` + `.gitignore` (4 fajla, +155/-17).

### Šta valja

- `RateLimitError` custom exception + propagacija iz `_run_entry` u `run_suite`
  (`runner.py:130-149`) — dobar refactor, ne guši grešku kroz generic `except Exception`.
- State fajl + STOP marker (`runner.py:25-36`) — `ralph.sh:37` već čita `STOP`,
  integracija radi out-of-box.
- Exit kod 2 razlikuje rate-limit od FAIL — Ralph može razlikovati u petlji.
- Auto-cleanup state-a na uspješan run (`runner.py:115-116`) — nema "stale resume" trap-a.
- `--offset` *i* `--resume` paralelno — manual override + auto.
- Partial verdicts se ipak zapisuju u JSONL prije exit-a (`runner.py:106-111`) —
  ne gubiš urađeno.

### Kritična rupa (MORA prije mergea)

**`app/main.py` nema exception handler za 429.**

Tok:
1. PWR vrati 429.
2. `openai.RateLimitError` se digne u `_run_pwr`.
3. FastAPI default uhvata i vraća **500 sa `{"detail":"Internal Server Error"}`**.
4. Eval client (`client.py:11-17`) gađa 5xx + frazu "rate_limit"/"overloaded" — **ali fraze nikad ne stignu do body-ja jer FastAPI ih sakrije**.
5. Detektor klasifikuje ovo kao običan server error → `_run_entry` ga uhvati kao
   generic Exception → entry dobije FAIL verdict.
6. **Resume se NE triggera.**

**Fix**: dodaj u `app/main.py` exception handler koji mapira `openai.RateLimitError`
(i Anthropic ekvivalent `anthropic.RateLimitError`) u 429 response sa porukom iz
SDK-a u body-ju. ~10 linija. Bez ovoga, mehanizam radi samo teoretski.

Skica:
```python
from fastapi import Request
from fastapi.responses import JSONResponse
import anthropic
import openai

@app.exception_handler(openai.RateLimitError)
@app.exception_handler(anthropic.RateLimitError)
async def rate_limit_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=429,
        content={"detail": f"rate_limit: {exc}"},
    )
```

### Manje rupe

- **`--limit 25` je guess** (`ralph/AGENTS.md`). Nema kalibracije — odakle 25?
  Pro/Max sesija nije 25 poruka. Treba mjerenje ili dokumentovani argument.
- **Partial verdicts iz više resume run-ova ne agregiraju u jedinstveni report.**
  Svaki resume = novi `runs/<label>_<ts>.jsonl`. Da bi rekao "95% kroz 250"
  moraš ručno mergovati. Sitnica ali bije Faza 1 acceptance metric.
- **`_RATE_LIMIT_PHRASES` pet generičkih fraza** (`client.py:11-17`) — fali
  "quota", "session limit", "credit", "claude pro", "tier"; možda i lokalizovane
  varijante. Lako dodati kasnije ali sad je krhko.
- **`print_summary` se zove na partial run** → izgleda "100% PASS na 17 entry-ja"
  iako je rate-limit prekinuo na 18. Misleading u ralph logu.

### Šta je Sonnet propustio

**Q1 (verdict cache) — nije ni dirao.** Rješenje gracefully stoji kad lupiš
limit, ali i dalje trošiš sesiju ponovo pokrećući entry-je koji su VEĆ PROŠLI u
prethodnom run-u. Cache je veći win — bez njega resume samo razmazuje trošak po
više sesija umjesto da ga eliminiše.

---

## Preporučeni redoslijed

### Prije mergea `feat/ralph-categories-eval-fix`

1. **Exception handler u `app/main.py`** za `openai.RateLimitError` +
   `anthropic.RateLimitError` → 429 sa SDK porukom u body. Bez ovoga cijeli
   mehanizam ne radi.
2. **`evals/runs/<label>/parts/` strukturu + `merge_parts.py` skriptu** da
   resume run-ovi imaju unified report za Faza 1 acceptance metric.

### Zaseban PR poslije

3. **Verdict cache** (Q1 #1) — `evals/cache/<hash>.json` lookup u runner-u.
4. **Tiered eval** (Q1 #2) — sample-first mode.

### Kalibracija paralelno

5. **Empirijski izmjeriti PWR ceiling** — voditi log kada lupiš limit i pri kojem
   broju poziva, da `--limit 25` zamijeniš stvarnim brojem (ili dokumentuješ
   kako si do 25 došao).

### Kasnije (Faza 1.5 ili kraj)

6. Proaktivni token budget tracker (Q2-B).
7. Prompt caching (Q1 #4) — Anthropic put.
8. Concurrent PWR calls (Q1 #5) — samo kad sesija nije bottleneck.
