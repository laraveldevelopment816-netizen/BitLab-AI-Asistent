---
date: 2026-05-22
branch: claude/analyze-category-hierarchy-dIVqm
participants: [Ivan, Claude]
topic: Evaluation Framework za BitLab AI asistenta + standardizacija na druge aplikacije (npr. Compliance Monitoring)
---

# Log

## Polazna tačka

Ivan: oba postojeća refactor plana u rutu (`EVAL-REFACTOR-PLAN.md`, `EVAL-REFACTOR-PLAN-v2.md`) ne odgovaraju. Hoće jednostavnije: testirati **full loop** kroz realan `/api/chat`, ali sa determinističkim verdiktima. Fokus drži na `evals/visualize_parent_runtime.py` jer je taj pristup pokazao realan problem (parent expansion, dovod do "smart routing → kategorija djeca" rješenja umjesto eksplozije kategorija u tool description). Krenuti korak po korak. Misli i o standardizaciji eval framework-a (npr. Compliance Monitoring).

## Što ima u `evals/` (informativni inventar)

- `visualize_parent_runtime.py` (33 KB) — runtime, LLM in loop, hvata tool args, mapira proizvode na kategorije preko cat tree. **Po Ivanu, kvalitetan baseline.**
- `visualize_parent_expansion.py` (25 KB) — deterministički simulator hard filtera, no LLM, no server.
- `run_e2e_html.py` (35 KB), `run_categories_html.py` (28 KB) — paralelni e2e runneri, preklapanja.
- `run_categories_cli.py`, `run_cli.py`, `run_categories.py`, `run.py`, `run_format.py`, `test_e2e_visual.py` — više starih ulaznih tačaka.
- Eval setovi: `parent_eval_set.json` (15 bare parent upita), `category_eval.json` (29 kvalifikovanih), `test_questions.json` (tool dispatch).

## Otvorena pitanja (za sljedeće korake)

- Što tačno znači "deterministički" u sprezi sa LLM-om u petlji — pretpostavka: LLM realno bira tool, ali validacija output-a je čist kod (bez LLM judge).
- Koji je prvi konkretan korak: minimalno generalizovati `visualize_parent_runtime.py` ili samo proširiti expect schema na postojećoj skripti?
- Šta je univerzalno (može se prenijeti na Compliance Monitoring), a šta je bitlab-specifično (cat tree, RAG)?

## Konkretan nalaz iz zadnjeg smoke run-a (`parent-runtime-smoke-20260522-214607.html`)

Smoke run sa 1 upitom ("Mobiteli"):
- Expected: `category_id=151` (Mobiteli parent), očekivani proizvodi iz subtree-a.
- Runtime: Claude **nije** zvao `search_products` — vratio je overview sa tri podkategorije (Mobilni telefoni 165, Dodaci za mobitele 129, Maske 1274) i tražio od korisnika da klikne / precizira.
- Verdict u HTML-u: **FAIL** (n_returned=0, routing_verdict=NULL).

**Suština problema (Ivan):** verdict logika u `visualize_parent_runtime.py` mjeri "broj proizvoda iz subtree-a" kao primarni signal. Za **bare parent** upit pametno ponašanje je upravo overview (ne search). To znači: skripta je trenutno **arhitektonski nesinhronizovana** sa novim tool design-om (smart "udari u parent → vrati djecu da klikne").

**Princip koji se nazire:** expect mora ovisiti o tipu upita:
- bare parent (npr. "Mobiteli") → expected verdict je *overview/children listing*, ne search.
- qualified (npr. "mobilni telefon do 500 KM") → expected verdict je *search_products* sa filterima i proizvodima iz subtree-a.

Korisnikova zadnja rečenica je presječena ("možete li vi napraviti sada da nam ovdje…") — čekam pojašnjenje.

## Update: Ivan pokrenuo limit=2 u drugoj Claude instanci

Eval set: "Mobiteli" + "Mobilni telefoni". Realno ponašanje:

- Oba upita → Claude pozvao `category_overview(151)`.
- Za "Mobiteli" to je **tačno** ponašanje.
- Za "Mobilni telefoni" Claude bira najbliži parent jer **schema enum za overview ne dozvoljava 175 (leaf)** — pa fallback ide na parent 151. To je očekivano za tu shemu, ali nije ono što proizvod-orijentisan upit traži.
- Eval u oba slučaja vidi NULL/FAIL jer parser u `visualize_parent_runtime.py:162` traži samo `search_products` rezultate, a `category_overview` reply ima drugi format.

Druga instanca Claude-a predložila dva fix-a paralelno:
1. Prompt 1b: leaf imena → `search_products(category_id=175)`, ne overview.
2. Eval parser: priznati `category_overview` kao validan routing.

**Ivan je vratio nazad: "Napravili ste početničku grešku. Dva paralelna fix-a → ne znaš koji je popravio."** Direktno povezano sa [[feedback-one-fix-at-a-time]].

Druga instanca prihvatila, redoslijed:
1. **Parser fix prvi.** Razlog: trenutno eval ne razlikuje "Claude pogrešno odlučio" od "Claude OK ali parser ne razumije". Bez tog razdvajanja, prompt promjena se mjeri pokvarenim instrumentom.
2. Očekivanje nakon parser fix-a: "Mobiteli" → PASS (overview(151) je tačno), "Mobilni telefoni" → konkretan FAIL sa verdiktom *overview(151) umjesto search_products(175)*.
3. Tek tada prompt fix-u može se pripisati efekt.

Druga instanca već najavila implementaciju parser fix-a: prepoznaje `category_overview` tool call + njegov reply oblik kao validan routing, dodaje novi verdict (radni naziv `PARENT_OVERVIEW`).

## Odluka: arhitektura parser fix-a

Ivan pitao da li dva odvojena fajla (search parser + overview parser) ili jedan parser sa pravilima.

**Odluka: jedan parser, dispatch po tool name** — ostaje u `visualize_parent_runtime.py` za sada (lokalna funkcija ili klasa unutar postojećeg fajla). Razlozi:
- Oba slučaja parsiraju **istu listu tool_calls** iz iste petlje — samo se dispatch-uje po tool name. Dva fajla bi imala vještačko granice.
- Preuranjena fragmentacija; YAGNI dok ne osjetimo bol.
- Kad dođemo do standardizacije (Compliance Monitoring), parser se *tada* izvlači u `evals/_lib.py` ili `evals/parsers.py` kao zaseban modul sa registry-jem. To je sljedeća iteracija, ne ova.

## Mini plan parser fix-a — šta tačno dirati

Trenutno stanje (`evals/visualize_parent_runtime.py`):
- `extract_search_calls()` (linija 181) — filtrira **samo** `search_products`. Sve ostalo ignoriše.
- `parse_products()` (linija 162) — markdown product regex; ne prepoznaje overview format ("📂 Ime (165)").
- `routing_verdict()` (linija 257) — enum: EXACT_PARENT / DESCENDANT / NULL / OUT.
- `result_verdict()` (linija 272) — enum: PASS / WARN / FAIL na osnovu broja proizvoda iz subtree-a.

**Šta mijenjam (jedan fajl, jedna iteracija):**

1. Nova funkcija `extract_overview_calls(tool_calls)` paralelno sa `extract_search_calls` — vadi `category_overview` pozive sa `parent_id` argumentom.
2. Nova funkcija `parse_overview_reply(reply)` — regex za "📂 Ime (count)" linije, vraća listu `{cat_name, cat_count}`.
3. Dispatch po tool name u main loop-u — prvi tool poziv određuje koja "ruta" se procjenjuje (overview vs search).
4. `routing_verdict` enum dobija `PARENT_OVERVIEW` (overview pozvan).
5. `result_verdict` dobija `WRONG_TOOL_TYPE` (npr. overview pozvan za upit koji je trebao biti search — Mobilni telefoni → overview(151) umjesto search_products(175)).
6. Default `expected_tool="search_products"` ako polje nije u eval entry — to čuva backward compatibility.

**Šta NE diram u ovom koraku:**

- `parent_eval_set.json` — invariant ([[feedback-test-case-invariant]]). Polje `expected_tool` se uvodi u eval set tek nakon što parser stoji i mjeri konsistentno. Tek tada je to čist sljedeći korak sa svojim A/B baselineom.

Output: novi smoke run pokazuje "Mobiteli" kao PASS (overview(151) prepoznato), "Mobilni telefoni" kao konkretan FAIL sa razlogom `WRONG_TOOL_TYPE: overview(151) umjesto search_products(175)`.

## Druga Claude instanca dala paralelan plan; gdje se moj razlikuje

Druga instanca:
- Generalizuj `extract_search_calls` → `extract_tool_calls` (jedna funkcija, hvata i `search_products` i `category_overview`).
- `routing_verdict` dobija grane: `OVERVIEW_PASS` (overview pozvan, cat_id se poklapa) i `OVERVIEW_WRONG` (overview pozvan ali pogrešan cat).
- `main()` loop puni novo `routed_tool` polje u row, prosljeđuje `routing_verdict`-u.
- HTML/JS: novi badge stilovi i labele za OVERVIEW_PASS/OVERVIEW_WRONG.
- **Samo `evals/visualize_parent_runtime.py`** — sve u jednom fajlu.

**Šta od mog plana ostaje korisno, a šta menjam:**

| Stvar | Drugi plan | Moj plan | Šta zadržati |
|---|---|---|---|
| Generalize parser funkciju | `extract_tool_calls` | Dvije odvojene | **Drugi** (DRY, lakše za buduće tool-ove) |
| Reply parsing za overview | Ne treba — tool_call nosi cat_id | `parse_overview_reply` markdown regex | **Drugi** (suvišan kod; pravi signal je u tool_call args) |
| Razdvajanje routing/result verdict | Sve u routing | `WRONG_TOOL_TYPE` u result | **Drugi** (čistije za overview slučaj koji nema produkte) |
| `result_verdict` za overview | Nije spomenuto | `WRONG_TOOL_TYPE` | **Hibrid:** za overview slučaj `result_verdict` = `NA` (not applicable), top-line ne računa kao FAIL |
| Eval set invariant | Nije spomenuto | Eksplicitno: ne diramo `parent_eval_set.json` u ovom koraku | **Moj doprinos** ([[feedback-test-case-invariant]]) |

Tj. moj plan je u 3 stvari poklopljen sa drugim, u 2 stvari je drugi bolji (parser DRY, no reply parsing), a moj jedinstveni doprinos je *eksplicitno čuvanje eval set invarianta + result_verdict=NA za overview slučaj da ne zagađuje top-line statistiku*.

## Parser fix implementiran (druga instanca)

Diff (+113/-57 u `evals/visualize_parent_runtime.py`):
- `extract_search_calls` → `extract_tool_calls` (hvata `search_products` + `category_overview` sa `tool` poljem).
- `routing_verdict` dobio `OVERVIEW_PASS` (overview tačan parent) + `OVERVIEW_WRONG` (overview na pogrešan parent, npr. leaf upit).
- `result_verdict` vraća `NA` za overview slučaj — ne miješa sa search PASS/FAIL.
- `main()` puni `routed_tool` u row dict.
- HTML/JS: novi badge stilovi (`overview_pass`, `overview_wrong`), nove stats kartice, top-line verdict broji `overview_wrong_count` kao "bad".

**Driftovi od mog plana koje treba notirati:**

1. **Eval set proširen** — `parent_eval_set.json` dobio "Mobilni telefoni" entry (leaf, expected `175`). Moj invariant princip je predlagao da se ne dira. Druga instanca je dodala (ne modifikovala) novi entry da bi se OVERVIEW_WRONG path uopšte testirao. Pragmatično opravdano (dodano, ne modifikovano), ali drift.
2. **`EXACT_PARENT` badge boja crveno → zeleno** — semantika promijenjena iz "ranjivost (najopasniji case bez parent_id expansion fix-a)" u "tačan target". Sa fix-om u kodu, EXACT_PARENT za leaf upit znači Claude je pošao baš target leaf — zeleno. Ali to je *drugi fix u istoj iteraciji* — sklizao scope.

## Smoke run sa parser fix-om (limit=2, label=parser-fix-smoke)

```
[ 1/2] 'Mobiteli'           NA   ruta=OVERVIEW_PASS   (29650 ms)
[ 2/2] 'Mobilni telefoni'   NA   ruta=OVERVIEW_WRONG  (19113 ms)

Total: PASS=0 WARN=0 FAIL=0 NA=2
Routing: OVERVIEW_PASS=1 OVERVIEW_WRONG=1
Wall: 48.8s
HTML: evals/runs/parent-runtime-parser-fix-smoke-20260522-223731.html
```

**Verdikt: parser fix radi.** Konkretni signali:
- "Mobiteli" → `category_overview(151)`, parent se poklapa → `OVERVIEW_PASS`. Eksplicitno PASS za dizajnirano ponašanje.
- "Mobilni telefoni" → `category_overview(151)` umjesto `search_products(175)` → `OVERVIEW_WRONG`. Konkretan razlog: schema enum za overview ne dozvoljava leaf 175, pa Claude fallback ide na parent 151.

Sada smo na čistom baseline-u: parser razlikuje "Claude pogrešno odlučio" od "Claude OK ali parser ne razumije". Sljedeći korak (zaseban, ne paralelan): prompt fix 1b — leaf imena → `search_products(category_id=175)`.

## CLI vs HTML nesklad → druga instanca dodala `overall_verdict`

Ivan primjetio: CLI pokazuje "1 prošao, 1 pao", HTML banner kaže "1 promašen" ali stats kartice se vidjele kao "sve loše". Problem: HTML banner gledao samo `pass_count` koji je u `summary` blok mapiran na **search PASS** (`result_verdict == "PASS"`), ne na overall. OVERVIEW_PASS je samim tim "nevidljiv" za banner.

Druga instanca dodala `overall_verdict(routing, result)`:
- NULL / NA / OUT → FAIL.
- OVERVIEW_PASS → PASS.
- OVERVIEW_WRONG → FAIL.
- EXACT_PARENT / DESCENDANT (search grane) → naslanjaju se na postojeći `result_verdict`.

Aggregate promjene:
- `pass_count` / `warn_count` / `fail_count` sad računaju iz **`overall_verdict`** (top-line, banner, terminal summary).
- Nove granularne metrike: `search_pass_count` / `search_warn_count` / `search_fail_count` (iz `result_verdict` samo za search rute), `overview_pass_count` / `overview_wrong_count` (iz routing_verdict).
- `avg_in_subtree` računa samo preko search redova (overview redovi nemaju produkte) — više se ne razvodnjava prosjek.

Leaderboard: badge sad uzima `overall_verdict || result_verdict` (backward compat sa starim run-ovima). Detail panel preimenovan iz `search_calls` u `tool_calls`, prikazuje overview pozive sa odvojenim renderom.

**Mišljenje:** Solidno. `overall_verdict` je čist sjedinjavajući signal — banner, leaderboard i terminal summary sad gledaju istu kolonu. Granularne metrike ostaju u stats kartice za debugging. Backward compat kroz `||` fallback je dobar potez. Pokretanje je opravdano — očekujemo terminal i HTML banner usaglašene: 1 PASS, 1 FAIL.

## Ključni nalaz: ponašanje sa istorijom razgovora je DRUGAČIJE

Ivan postavio pitanje — zašto "Mobilni telefoni" pada u skripti, a na widget-u prolazi.

**Test (direktan `curl` ka `/api/chat` sa simuliranom istorijom):**

```bash
curl -X POST /api/chat -d '{
  "message": "Mobilni telefoni",
  "history": [
    {"role": "user", "content": "Mobiteli"},
    {"role": "assistant", "content": "Mobiteli — šta tačno tražite? 📂 Mobilni telefoni (165), ..."}
  ]
}'
```

**Rezultat:**

```
tool_calls: search_products · {"query":"mobilni telefoni","category_id":"175","top_k":10}
reply: Evo trenutne ponude mobilnih telefona: 1. iPhone 17 256GB White eSim — 1.899 KM ...
```

Claude sa istorijom **tačno bira `search_products(175)`**. Bez istorije (cold scenario u skripti) bira `category_overview(151)`.

**Zašto:** schema enum za `category_overview` ne dozvoljava leaf 175. Cold case → Claude fallback ide na parent 151 (overview). Warm case → kontekst razgovora ("ovaj korisnik je već vidio overview, pa traži konkretan leaf") navodi Claude-a da preskoči overview i ide direkt search.

**To znači:**

- Sistem **radi kako je dizajniran** u realnom widget flow-u.
- Eval skripta sa praznom istorijom **uhvatila divergenciju** koju widget ne pokazuje. **To je vrijedan signal**, ne bug u eval-u.

## Way forward — kako proširiti framework da pokrije obje strane

Konceptualno: eval set dobija **dimenziju "history scenario"**.

| Scenario | Kako simuliramo | Šta mjeri |
|---|---|---|
| `cold` (default) | `history=[]` | Da li sistem radi *bez konteksta* — korisnik dolazi sa Google search-a sa leaf imenom |
| `warm:overview_first` | `history=[user_turn_parent, assistant_turn_overview]` | Da li sistem radi *kroz UX flow* — korisnik kuca parent → klikne leaf |

Implementacija (samo skica, ne sad):
- Eval entry dobija opciono `history` polje (lista turn-ova ili semantički tag).
- Parser proširuje payload ka `/api/chat` sa tom istorijom.
- Test case **invariant**: postojeći set ostaje cold. Warm verzije se dodaju kao **paralelne nove entry-je**, ne kao modifikacije.
- Razlika u verdiktu (cold FAIL, warm PASS) eksplicitno pokazuje "kontekst-zavisan" gap — što je za prompt fix targeted, ne za eval rewrite.

**Pitanje za Ivana (čekam odgovor):** šta je realni UX cilj?

1. Cold scenario *takođe* treba raditi (jer korisnik može doći direkt sa Google search-a, deep link-a, voice intent-a sa leaf imenom) → sistemski fix u prompt-u ili schema-i za `category_overview` (dozvoliti leaf?).
2. Cold scenario *nije realan* (uvijek dolazi kroz widget UX gdje history postoji) → eval skripta treba da podrazumijeva warm, dodajemo history simulaciju.

Mišljenje: opcija 1 je vjerovatnija — voice intent i Google ulazi su realni; sistem treba biti robust na cold leaf imena.

## Odluka: tri eval seta + skica finalnog framework-a (po Ivanovom razmišljanju)

Ivan: cold scenario **ostaje** (vrijedan signal koji se ne hvata preko widget testa od vrha ka dnu). Multi-turn (sa istorijom) dolazi kao **dodatak**, ne zamjena. Tri smjera:

| Set | Domen | History | Šta mjeri |
|---|---|---|---|
| `categories_cold` | bare kategorije (parent + leaf imena: "Mobiteli", "Mobilni telefoni") | `[]` | Tool dispatch — overview vs search za leaf bez konteksta |
| `products_cold` | qualified product upiti ("gaming miš do 100KM", "iPhone 17", "laptop sa Ryzen 7") | `[]` | Search relevance — top-k unutar subtree-a, filteri, brand match |
| `multi_turn` | UX flow: prethodni turnovi pa kvalifikovan upit | non-empty | Kontekst-svjesno ponašanje (widget realtime) |

Ivanova poenta: "**nije filozofija**" — kad imamo te tri komponente, samo podešavamo redoslijed pitanja u testovima.

### Skica finalnog framework-a (pravila)

**Direktorijum:**

```
evals/
  sets/
    categories_cold.json
    products_cold.json
    multi_turn.json
  runtime_eval.py           # jedan engine, čita N setova
  _lib.py                   # parsers, verdict, HTML render (kasnije ekstrakt)
  runs/
    <label>-<timestamp>.html
```

**Entry schema (unificiran preko svih setova):**

```json
{
  "query": "Mobilni telefoni",
  "history": [
    {"role": "user", "content": "Mobiteli"},
    {"role": "assistant", "content": "..."}
  ],
  "expect": {
    "tool": "search_products",
    "category_id": "175",
    "category_subtree": "151",
    "min_results": 3,
    "max_results": null,
    "args_subset": {"max_price_km": 100},
    "forbid_products": []
  },
  "tags": ["leaf", "voice-likely-intent"]
}
```

Polja koja ne važe za dati upit se izostavljaju. Engine zna kako da obradi svaki ključ — `tool` provjerava routing, `category_subtree` provjerava da li su proizvodi u subtree-u, `args_subset` provjerava prosleđene argumente, itd.

**Verdict pipeline (jedan, naslanja se na postojeće):**

`routing_verdict` → `result_verdict` → `overall_verdict` (već implementirano za jedan set; rade nezavisno od koja je grupa).

**CLI:**

```bash
python evals/runtime_eval.py                                  # svi setovi
python evals/runtime_eval.py --sets categories_cold            # samo jedan
python evals/runtime_eval.py --sets categories_cold,multi_turn # više
python evals/runtime_eval.py --label v2-prompt-fix             # za A/B compare
python evals/runtime_eval.py --limit 3                         # smoke per-set
```

**HTML output (jedan fajl, više sekcija):**

- Top-line: aggregat globalno (PASS/WARN/FAIL kroz sve setove).
- Po-set sekcija: vlastiti banner, stats kartice, leaderboard, detail panel.
- Cross-set tabela: ista query / scenario u različitim setovima (npr. "Mobilni telefoni" cold vs warm) — vizuelno upoređivanje gdje je razlika.

**Pravila koja čuvamo:**

- Eval setovi su **invariant** — ne mijenjaju se kad mijenjamo prompt; tek kad mijenjamo *šta testiramo* (novi scenario, novi tool).
- **Coverage auto-gen** za `categories_cold` iz `PARENT_CATEGORIES` u `app/tools.py` — ručno se ne održava.
- **Jedan fix u jednom trenutku** ([[feedback-one-fix-at-a-time]]) — kad mijenjamo prompt, jedan run prije + jedan poslije, ne paralelno mijenjati instrument.
- **Backward compat** — `r.overall_verdict || r.result_verdict` pattern (već postoji) ostaje za stare run-ove.

Ovo je prvi konkretan oblik gdje vidimo "finalni framework" — još nije implementirano, ali strukturno ovako ide. Ne radimo sve odjednom: prvo dovršimo cold case fix (sljedeći korak), pa generalizujemo engine na više setova kao slijedeća iteracija.

## ASCII tree kategorija — generisan u `category_tree.txt`

Ivan tražio tree da bi razmislio o pravilu "ako nema djece → uvijek vraćaj proizvode (search)".

Statistika cijelog stabla (238 aktivnih kategorija, 5287 proizvoda):

| Tip | Broj | % | Cilj tool |
|---|---|---|---|
| Leaf (bez djece) | 209 | 88% | `search_products` |
| Parent sa djecom | 29 | 12% | `category_overview` |
| Parent sa ≥2 djece (validan za overview enum) | 26 | 11% | `category_overview` |
| Root-level (parent_id=0) | 41 | — | mixed |

**Ivanovo predloženo pravilo:** "ako kategorija nema djece → uvijek search_products" pokriva **88% kategorija** automatski iz strukture. Preostali parent slučajevi (12%) — Claude treba znati da pozove overview.

To je čista deterministička pravila bazirana na strukturi stabla, ne na imenu kategorije. Implementaciono može živjeti u:
- `app/tools.py` — schema enum za `search_products.category_id` može biti **svaki cat_id sa 0 djece** (leaf), za `category_overview.cat_id` **svaki cat_id sa ≥2 djece**. Tako Claude fizički ne može pozvati overview za leaf — schema ga sprečava.
- Prompt bi onda samo trebao reći "ako je upit kategorija imenom, pozovi odgovarajući tool"; schema ga vodi na pravi.

Tree fajl: `docs/brainstorm/2026-05-22-eval-framework-standardizacija/category_tree.txt`. Putanja poslana u dictate panel za klik-kopiraj.

## Pre-router skica (na Ivanov zahtjev)

Detaljni ASCII flow + pseudokod + test plan + otvorene odluke u `pre_router_sketch.txt`.

Suština: novi modul `app/prerouter.py` (~50 LOC) ispred Claude-a. Normalizuj input → guard (cijena/brend/kompleksnost) → exact name match → dispatch (leaf=search, parent=overview) ili fall-through u Claude. 100% deterministic za bare category name upite, Claude radi sve ostalo.

## Ivanov akcioni plan (way forward)

Ivan se dopada skica. Predlaže redoslijed:

1. **Sada:** commit + push trenutnog parser fix-a — radi druga instanca, ne ova sesija.

2. **Iduće: razdvojiti eval u dva nezavisna seta**
   - **Cold kategorije:** lista **svih** aktivnih kategorija (238) sa pozitivnim primjerima — ime kategorije → očekivani tool dispatch. Plus **negativni primjeri** kvalifikovani sa očekivanjem da padnu ("automobili", "xyz", ambiguous imena). Ako padne kako je očekivano → PASS (očekivanje ispunjeno). Ako prođe → false positive, znak da je sistem previše permisivan.
   - **Cold search products:** kvalifikovani upiti (sa cijenom, brendom, modelom) — opet pozitivni + negativni.
   - **Vizualno razdvojeni dashboard-i** — kategorije i produkt search ne mješamo u istom HTML-u.

3. **Tek onda: pre-router kao top layer.** Sa solidnim baseline-ima vidimo šta će da prođe a šta padne sa pre-routerom; A/B compare daje odgovor.

4. **Cilj:** pojednostaviti, ali bolje hvatati pravilnosti i nepravilnosti.

### Šta dodajem (moja dva doprinosa Ivanovom planu)

a) **Pozitivne entry-je za kategorije auto-generišemo iz `data/categories.csv`** — 238 ručno održavati je preuranjena bol. Skripta `scripts/gen_categories_eval.py` čita CSV, za svaki aktivni cat generiše entry sa `expected_tool` (leaf → search, parent ≥2 djece → overview), `expected_category_id`, `tags: ["auto-gen"]`. Negativni se održavaju ručno.

b) **Negativni set ima eksplicitan razlog padanja** — polje `expect.failure_reason`:
   - `"not_in_catalog"` — kategorija ne postoji u BitLab-u ("automobili").
   - `"ambiguous_name"` — naziv koji se preklapa sa više pojmova ("kabl" — može biti USB/audio/video).
   - `"typo_likely"` — vjerovatna typografska greška ("mobitejli").
   - `"out_of_scope"` — pojam koji nije proizvod ("povraćaj robe", "garancija").

Tako kad negativni entry padne, vidimo *zašto* je očekivano da padne — razdvajamo "sistem pravilno odbio" od "sistem ne razumije šta od njega tražimo".

### Mišljenje

Plan ide u dobrom smjeru. Razdvajanje seta + invarijantni negativni primjeri = bolji signal/šum. Pre-router kao top layer **tek nakon** što oba baseline-a stoje — slijedi [[feedback-one-fix-at-a-time]]. Way forward potvrđen.

## Update: druga instanca već refaktorisala strukturu

Provjereno stanje:

```
evals/
  README.md
  run_categories.py          # PLACEHOLDER (13 LOC docstring, no implementacija)
  run_products.py            # PLACEHOLDER (16 LOC docstring, no implementacija)
  sets/
    categories_cold.json     # 245 entry-ja (235 auto-gen + 10 manual negative)
  archives/
    visualize_parent_runtime.py   # stari engine, RADI ali zna stari format
    ... (svi raniji eval skripta)
  runs/
```

`categories_cold.json` ima **novi schema** — `expect.tool`, `expect.category_id`, `history`, `tags`. Arhivska `visualize_parent_runtime.py` traži **stari schema** — `expected_category_id`, `category_label`. Šema mismatch.

## Ivanov novi zahtjev: kako pokriti products bez promjene koda

Pitanje: može li arhivska skripta da radi za products bez izmjena?

**Odgovor: DA, ako se products_cold.json napravi u STAROM formatu.** Šema mismatch postoji samo za nove fajlove (`categories_cold.json`). Stari engine prima `expected_category_id` direktno iz JSON-a (`run_categories.py:703-704` u arhivskoj verziji).

### Plan minimalne invazije

1. Kreiraj `evals/sets/products_cold.json` u **starom formatu** sa product upitima:
   ```json
   [
     {"query": "iPhone 17", "expected_category_id": "175", "category_label": "Mobilni telefoni / iPhone"},
     {"query": "gaming miš do 100 KM", "expected_category_id": "222", "category_label": "Miševi i grafički tableti"},
     ...
   ]
   ```

2. Pokreni arhivsku skripte:
   ```bash
   python evals/archives/visualize_parent_runtime.py \
     --queries evals/sets/products_cold.json \
     --label products-cold-smoke \
     --limit 5
   ```

3. Output: `evals/runs/parent-runtime-products-cold-smoke-<TS>.html`.

4. **Verdikt logika već radi za product upite:**
   - Claude pozove `search_products(cat_id=X, max_price_km=Y, brand_id=Z, query=...)`.
   - `routing_verdict` → `EXACT_PARENT` (cat_id se poklapa sa expected) ili `DESCENDANT` (smart routing).
   - `result_verdict` → PASS ako ≥3 proizvoda iz subtree-a.
   - `overall_verdict` → naslanja se na result za search grane.

5. **Šta NE radi bez izmjena (refaktor kasnije):**
   - Filter verifikacija (`max_price_km`, `brand_id` u args_subset) — nije implementirano u arhivskoj skripti.
   - HTML naslov će i dalje reći "Parent kategorije" za product run — kozmetika, label u file imenu razdvaja.
   - Novi tags / failure_reason iz schema nisu korišćeni.

**Ovo daje smoke signal za product upite SADA**, bez engine rada. Refaktor (`run_products.py`) može doći nakon što vidimo šta arhivska skripta već hvata a šta promaši.

### Drift od mog ranijeg plana

Ranije sam predložio "auto-gen products entry-ja iz categories.csv". Za products to ne radi — products imaju kvalifikatore (cijena, brend, model) koji nisu u CSV-u. Auto-gen je validan za kategorije (245 entry-ja iz 238 cat-ova), ali za products treba ručna kreacija. Manji set (10-30) sa pažljivim odabirom je bolji od velikog auto-gen šuma.
