---
date: 2026-05-20
branch: staging
session: 2026-05-20-bitlab-parent-kategorije
---

# decisions — BitLab parent kategorije

## 1. Kako čitati `parent-expansion-*.html`

- **Verdict banner je primary signal.** Zeleno PASS = fix je u `app/rag.py` (sve tri heuristike — `_load_cat_descendants` helper, `self._cat_descendants` polje, set membership filter — vraćaju YES). Crveno FAIL = fix nije u kodu.
- **`current` vs `alternative`.** Skripta inspektuje `app/rag.py` na disku i prema `fix_applied` stanju mijenja značenje kolona: kod PASS-a `current = subtree` (velika brojka), kod FAIL-a `current = direct` (mala). Alternative je drugi mod ("bilo bi").
- **Leaderboard + verdict banner = 90% potrebnog uvida.** Tree (kompletan hijerarhijski prikaz) je za detaljnu analizu kasnije, na prvi pogled se ignoriše.
- **Cat 17 Računari je didaktički primjer, ne primarni impact.** U leaderboard-u je 7. po delti (+177); stvarni top je cat 151 Mobiteli (+1570), zatim 219 PC periferija (+638). Docstring skripte koristi cat 17 jer je intuitivan ("Računari → Notebook/Tablet/Desktop"), ali fix najviše pomaže drugim parent kategorijama.

## 2. Branch realnost — fix je SAMO na feature granu

- Provjereno empirijski (`git show staging:app/rag.py | grep …` i isto za main): `staging` i `main` u `bitlab-ai-asistent` repo-u **nemaju** ni `_load_cat_descendants` ni set membership filter.
- Fix postoji samo na `claude/analyze-category-hierarchy-dIVqm` (gdje je `parent-expansion-20260520-154321.html` generisan, PASS banner).
- **Posljedica:** staging pretraga sa eksplicitnim `category_id=219` (PC periferija) vraća 0 proizvoda. Za cat 151 Mobiteli: 5 direktnih. Za cat 17 Računari: 20. Velike brojke iz leaderboard-a (1575, 638, itd.) dolaze tek nakon merge-a u staging.
- **Merge nije zakazan u ovoj sesiji** — user je svjesno pomjerio fokus na druge stvari. Otvoreno za sljedeću sesiju.

## 3. Paradoks "staging vraća rezultate bez fix-a"

User je empirijski testirao "PC periferija" na staging-u i dobio relevantne proizvode (miševi, tastature, podloge, slušalice). To je u suprotnosti sa "0 proizvoda kod cat 219" teorijom — paradoks razriješen kroz **tri nezavisna sloja zaštite** koji djeluju i bez parent fix-a:

1. **Hibridna pretraga bez `category_id` hard filtera** (`app/rag.py:322`): BM25 + vektorski embeddings prolaze kroz svih 5287 proizvoda i rangiraju po fusion score (0.6 vektor + 0.4 BM25). Embedding "PC periferija" je u vektorskom prostoru blizu "miš", "tastatura" — semantička sličnost ih izvlači gore.
2. **Smart LLM routing** (`app/tools.py:64`): Claude vidi listu kategorija sa labelama u tool description-u i može odlučiti da NE pošalje parent `category_id`, ili pošalje child (npr. cat 277 = Miševi). Praktično, LLM zaobilazi problem.
3. **Soft category boost** (`app/rag.py:339`, `_detect_intent_categories`): bez hard filter-a sistem tokenizuje query, mapira preko `category_terms.json`, i dodaje `+0.25` boost score svim proizvodima u match-ovanoj kategoriji.

**Implikacija:** parent fix je **defensive depth, ne primary win.** Pokriva edge case kad agent ipak eksplicitno pošalje parent `category_id` (recimo poslije sistem-prompt promjene). Tipičan UX scenario je zaštićen LLM slojem.

## 4. Workflow correction — server komande

- **User pokreće sve server komande sam** preko click-to-copy u `/dictate` panelu (`scripts/cmd.sh "..."`). AI ne nudi da SSH-uje, čak ni za read-only diagnostike.
- Razlog (user-ova rečenica): *"ne mi pokrećeš komande na serveru, ja pokrećem komande na serveru"*. Postojeća memorija `feedback_no_server_changes_without_approval.md` je ažurirana sa Voice-mode addendum-om (2026-05-20).
- **Triger primjer:** staging.aiasistent.bitlab.rs vratio 502 zbog ručno stopiranih servisa. Umjesto da Claude predloži `ssh + systemctl status`, ide `cmd.sh "sudo systemctl list-units --type=service --state=inactive,failed"` za user-a da pokrene.

## 5. Server services runbook

- **Napravljen** `bitlab-ai-asistent/deploy/RUNBOOK-services.md` (~150 linija). Dosadašnja `deploy/RUNBOOK-prod.md` je samo za inicijalni setup, ne za daily ops.
- **Sadrži:** tabela 4 servisa sa portovima i RAM-om (`aiasistent-prod` 8000, `aiasistent-staging` 8001, `n8n-prod` 8030, `n8n-staging` 8031), status komande (`list-units`, `ss -tlnp`, memory check), start/stop/restart (pojedinačno + bulk), `journalctl` recepti, health check-ovi iz lokalnog WSL-a, nginx ops, i konkretan recovery scenario za "staging pao zbog memorije" incident pattern.
- **Karakter:** svaka komanda u zasebnom code blocku → kompatibilno sa click-to-copy iz dictate panela.

## 6. Runtime visualizer — `evals/visualize_parent_runtime.py`

- **Napravljen** `bitlab-ai-asistent/evals/visualize_parent_runtime.py` (~400 linija) kao sibling `visualize_parent_expansion.py`-ja. Isti UI šel (dark theme, verdict banner, stats kartice, leaderboard tabela, expandable per-query detalji), drugi data layer — pravi HTTP poziv ka `/api/chat` umjesto deterministička simulacija.
- **Query set:** `evals/parent_eval_set.json` — 15 upita, svaki je doslovno ime parent kategorije iz leaderboard-a (Mobiteli, PC periferija, Računari, …).
- **Verdict logika:**
  - Routing: `EXACT_PARENT` (Claude poslao baš parent — opasno), `DESCENDANT` (poslao child — smart), `NULL` (bez filtera — soft boost), `OUT` (van subtree).
  - Result: `PASS` (≥3 proizvoda u expected subtree), `WARN` (1–2), `FAIL` (0).
- **Versioning:** `--label v1-baseline` / `--label v2-prompt-tweak` ulazi u filename → regression compare otvaranjem dva HTML-a side-by-side.

## 7. `top_k` ograničenje — odgovor

- `search_products` tool ima `top_k` default=5, max=10 (`app/tools.py:114–118`).
- **Posljedica:** jedan tool poziv vrati maksimum 10 proizvoda. Multi-iteration turn može vratiti do ~30. Nikada svih 638 iz PC periferija subtree-a.
- **Agent paradigma:** "top-K + LLM curated", ne "list all". Ako se želi "list all" semantika, treba separate endpoint mimo agent loop-a.

## 8. Debug runbook — `RUNBOOK-debug.md`

- **Napravljen** `bitlab-ai-asistent/RUNBOOK-debug.md` (~250 linija). 6 sekcija:
  1. Pokretanje servera (uvicorn na 7778 za eval, 8000 za prod sim + vite proxy), vite dev za dashboard frontend, sibling playwright-router.
  2. Eval skripte (tabela sa primjenom svake) + komande za svaku.
  3. Dashboard tabovi i kolone za debug — Requests, Request detail (`tool_calls[]` sa `iteration`, `tool_name`, `input_json`, `output_text`, `latency_ms`), Sessions, Stats, Errors, Overview, Compare.
  4. **Agent loop primer:** *turn* = razmijena user ↔ agent. *Iteracija* = unutar jednog turn-a, agent ↔ tool petlja. Default `max_tool_iterations=10`.
  5. Pet quick debug recepta za najčešće scenarije.
  6. Linkovi na ostale runbook-e.

## 9. Otvoreno za sljedeće sesije

- **Claude Code output style standard** u `bitlab-standards`. User je zaključio da voice-style sažeti odgovori (2-3 rečenice po turn-u, bez markdown headera i code dump-ova) bolje rade za njega u text mode-u kad je umoran. Predlog: nova brainstorm sesija (slug npr. `claude-code-voice-like-output-style`), standard doc u `docs/standards/`, plus konkretan output-style fajl koji se može staviti u `~/.claude/output-styles/`.
- **Dashboard widget za routing vidljivost** u realnom razgovoru. Da prestane biti black box "ne znamo koju kategoriju je Claude pozvao". `tool_calls` već idu u `_persist_trace` → baza → dashboard API; proširenje je u dashboard frontend-u (`bitlab-ai-asistent/dashboard/`).
- **Strukturirani JSON output** iz LLM-a za određene kategorije (već u user-ovom planu za prompt modifikacije).
- **Merge `claude/analyze-category-hierarchy-dIVqm` → staging** kad bude vrijeme za parent fix u produkciji. Trenutno na feature grani, staging neutaknut.
- **Empirijski v1 baseline run** — pokrenuti `visualize_parent_runtime.py --label v1-baseline` da se potvrdi koliko je `EXACT_PARENT` routing rijedak u praksi (potvrda hipoteze iz tačke 3).

---

## Sesija 2 (2026-05-21) — odluke iz hard testinga

### 10. Silent exception swallowing je arhitekturni bug, ne UX problem

`app/tools.py:dispatch` je imao generičan `except Exception` koji je svaku sistemsku grešku (RAG indeks pukao, FAISS dimensiona mismatch, model nije loadovan) prevodio u tekstualnu poruku *"Pretraga trenutno vraća prazan rezultat..."*. Claude je tu poruku tumačio kao legitiman empty result i halucinarao izmišljene proizvode (konkretno: 6 Samsung Galaxy A56/A36/A16 modela sa 256GB konfiguracijama koje ne postoje u bazi). Korisnik je vidio "validan" odgovor sa lažnim proizvodima, bez ikakvog signala da je sistem u problemu.

**Odluka**: razdvojiti expected (`ToolValidationError`) od unexpected (sve ostalo). Expected ide kao Claude-friendly poruka; unexpected propagira do `/api/chat` → HTTP 503 sa structured payload-om. Frontend već čita `data.reply` (postojeći pattern), prikazuje kao bot poruku *"Imamo tehnički problem sa katalogom..."*. Princip: **fail-fast > silent fail** za search/RAG slojeve. Vidi `app/tools.py:ToolValidationError` + `app/main.py:_system_exception_handler`.

### 11. Silent dependency upgrade je glavni izvor regresija

`torch` constraint `>=2.4,<3.0` u `pyproject.toml` je 1. maja kroz `pip install -e .` resolvao na torch 2.11.0 — bez ikakvog manuelnog akcije. Sentence-transformers interno ponašanje (`SentenceTransformer(..., device="cpu")`) se promijenilo između torch 2.x i 2.11 — sa istom verzijom sentence-transformers, kod koji je bio FIX postao je BUG (meta tensor lazy load). Bug postoji 3 sedmice, manifestovao se tek sad jer warmup nije bio aktiviran u međuvremenu.

**Odluka**: pin exact verzije za core RAG dependencies. `torch==2.11.0`, `sentence-transformers==3.4.1`. Komentar u kodu eksplicitno opisuje incident — da niko ne otvori opseg ponovo. Plus, startup smoke test (`_warmup_rag_sync`) hvata regression pri boot-u prije nego stigne prvi korisnik. **Industrijski standard za production search/RAG: pin sve transitivne zavisnosti (uv.lock / requirements.lock)**, ne samo top-level constraint-e.

### 12. `/healthz` ima readiness semantiku, ne liveness

Defaultni K8s pattern je `/healthz` = liveness (proces živ) + `/readyz` = readiness (sloj spreman). Pošto nemamo dva odvojena endpoint-a a praktično treba readiness signal, `/healthz` sad vraća **HTTP 503 dok `_rag_ready=false`**, **200 inače**. Body je isti payload (sa `rag_error` porukom) da operativci vide ZAŠTO. Load balancer pravilno tretira instancu kao not-ready dok RAG warmup nije završio (50s prvi put na WSL2).

### 13. Output token limit je arhitekturni — ne može se "podići u config-u"

Korisnik je tražio da Claude vrati svih 1575 proizvoda u jednom chat odgovoru. To je ~200-250K markdown tokena. Anthropic API hard cap je 64K (sa beta header-om 128K); preko PWR/Claude.ai web efektivno ~8-12K. **Fundamentalno ne staje** u jedan response, bez obzira na config. Za "list all" treba zaobići agent loop: separate `/api/products?category_id=151&include_descendants=true` koji vraća JSON direktno iz RAG-a. Tehnička limitacija LLM API-ja, nije bug.

### 14. Test case je invariant kad podešavamo sistem

Tokom sesije sam zamutio dva nezavisna lijevera istovremeno (povisio `top_k` schema cap I preformulisao eval query "Mobiteli" → "Pokaži mi sve mobitele..."). Korisnik me ispravio: *"Test case je safety net da možemo da tvikujemo parametre sistema. Ako mijenjamo i test i sistem u istom potezu, ne znamo šta je uzrok promjene u rezultatu."* — A/B compare gubi smisao. Memorija `feedback_test_case_invariant.md`.

### 15. Voice komunikacija ide na prirodnom jeziku, ne tehničke kratice

Korisnik prati glasom dok radi druge stvari (chat widget, dashboard, terminal). Tehnički termini iz koda (`WARN`, `subtree`, `EXACT_PARENT`, `DESCENDANT`, `cat 175`) ne znače mu ništa bez vizualnog konteksta. Memorija `feedback_natural_language_voice.md`: prevodi sve na ljudski — *"upozorenje"*, *"porodica"*, *"smart rutovao u podkategoriju"*, *"kategorija mobiteli"*. Tehnička imena ostaju samo za fajl/funkcijske reference (`visualize_parent_runtime.py`) i click-to-copy komande.

### 16. Mapiranje proizvoda na kategoriju ide preko URL hash-a, ne imena

Claude reformuliše imena u svom reply-ju (skraćuje, izbacuje zareze, gubi model-kod sufikse). URL hash (G-kod prefix iz `urlhash` polja u `all-products.json`) je stabilan identifier — Claude ga doslovno kopira iz tool result-a. Skripta `evals/visualize_parent_runtime.py` sad mapira proizvod → kategoriju preko: (1) `urlhash` egzakt match, (2) G-kod prefix, (3) name egzakt, (4) name lower-case, (5) name prefix substring. Pet slojeva fallback-a. Rješava sve dotada-null mapiranja iz prošlih run-ova.

### 17. `--reload` ne ponavlja lifespan task — pun-restart za state-aware promjene

uvicorn `--reload` watcha `.py` fajlove i triger-uje child process restart pri code change. Pun-restart UVIJEK pokupi fresh ENV i pokrene lifespan. **Ali**: mijenjanje `.env` samostalno (bez `.py` izmjene) NE triger-uje reload, jer watcher ne gleda `.env`. Plus, kad reload se zaista desi, neki state-aware obrasci (FastAPI `lifespan` task koji setuje module-level globalne varijable poput `_rag_ready`) mogu da budu skipped u određenim scenarijima. Pouka: za bilo šta sa state-om — pun manuelni kill+restart, ne `--reload`. `--reload` je strogo development-only feature za "fast iteration nad REST handler izmjenama".

### 18. Hard-testing override-i moraju imati komentar koji ih veže

Sa 6 mjesta gdje smo digli timeout-e i token limite, lako se zaboravi vratiti. Svaki override ima komentar koji eksplicitno kaže (a) **trenutnu vrijednost**, (b) **šta je bilo prije**, (c) **kad vratiti** ("prije produkcije" / "prije merge-a") i (d) **link na pratnju** (gdje su uparenа druga mjesta). Tako da niko (čovjek ili LLM) ne može da vidi 1800s i pomisli da je to namjerno za produkciju.

Hard-testing override-i ostavljeni u working tree-u, nije commit-ovano. Mapa za vraćanje u Sesija 2 sekciji `log.md`.
