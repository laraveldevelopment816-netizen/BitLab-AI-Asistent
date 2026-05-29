# Eval failure analysis — 2026-05-23

> **Predloženi refaktor:** [SSOT-categories-refactor-plan.md](./SSOT-categories-refactor-plan.md)
> — plan za svođenje 4 izvora kategorija + 1 brand fajla na single-source dizajn,
> što rješava root cause opisan u sekciji "Root cause" niže.

Analizirani jutrošnji smoke run-ovi (oba bez server grešaka — server flakiness
nije faktor):

- `evals/runs/categories-smoke-20260523-070231.html` — 50 queries, 21 PASS / 29 FAIL
- `evals/runs/products-smoke-20260523-071544.html` — 21 queries, 17 PASS / 4 FAIL

Sinoćnji run-ovi (00:30-01:22) imali su 26/50 server grešaka (HTTP 503 +
ReadError + RemoteProtocolError) — to je tretirano u prethodnom turn-u i
ne ulazi u ovaj nalaz. Server flakiness se NIJE reprodukovao danas;
mogući uzrok je Anthropic API peak vrijeme (~01:00 UTC = US prime time)
ili akumulirana PWR backend degradacija. Vraćamo se na to ako se opet
pojavi, ovaj nalaz pokriva samo semantic FAIL-ove.

## Root cause (jedan uzrok pokriva većinu)

Tri različita data source-a za kategorije u istom tool sistemu, NIJE u
međusobnoj sinhroniji:

| fajl | size | uloga | koristi se u |
|---|---|---|---|
| `data/categories.json` | 50 entries (AI-curated bucket-i sa labelama) | enum za `search_products` tool | `app/tools.py:121-122, 150, 176` |
| `data/categories_new.json` | 255 entries (real taxonomy, status=1) | enum za `category_overview` tool | `app/tools.py:133-138, 309` |
| `data/categories.csv` | 513 entries (full taxonomy uključujući inactive) | parent expansion u hard filter-u | `app/rag.py:26-67` |

Migracija ka `categories_new.json` JE krenula — `category_overview` tool
je migriran (vjerovatno tokom rada na kartici `covt` u Doing). Ali
**`search_products` (glavni tool) i dalje vidi stari 50-entry enum** iz
`categories.json`. To je polu-migracija.

Posljedica: kad Claude vidi upit "Inkjet printeri" → traži najbliži match
u svom enum-u → ne nalazi 126 (nije u 50 bucket-a) → fallback na 125
("Printeri raznovrsni") koji JE u enum-u sa 19 proizvoda. Eval testira
prema `categories_new.json` gdje 125 NE POSTOJI, pa se to računa kao OUT.

Hard filter u `rag.py` (`categories.csv`) i AI enum (`categories.json`)
takođe NISU u sinhroniji — Claude može poslati ID koji nije u CSV-u
(npr. 125), pa `_load_cat_descendants().get("125", {"125"})` vrati samo
{125} bez parent expansion-a, što daje 19 proizvoda umjesto očekivanih
~120 iz subtree-a 97 → {124, 125, 126, 127, 128, 129, 130, 131, 337}.

Eval (`evals/run_categories.py:42, run_products.py:43`) koristi
`categories.csv` za parent expansion ground truth + `categories_new.json`
preko `scripts/gen_categories_eval.py` za generaciju expected_cat_id.

Najvažniji pojedinačni dokaz: cat 125 ("Printeri raznovrsni — Epson, HP,
Canon", 19 proizvoda) postoji **samo** u `categories.json` (AI-curated
bucket). Ne postoji u `categories_new.json` ni u `categories.csv`. Claude
šalje 125 za sve printer upite jer mu se u tool description-u ta labela
nudi.

## Failure clusters (categories run 07:02)

### Cluster A — OUT routing (7 fails, svi printer cat-ovi)

| query | expected | routed |
|---|---|---|
| Laserski printeri | 124 | 125 (Printeri raznovrsni) |
| Inkjet printeri | 126 | 125 |
| Multifunkcijski printeri | 127 | 125 |
| Kopir aparati | 128 | 125 |
| Foto printeri | 129 | 125 |
| Matricni printeri | 130 | 125 |
| Desktop Brand Name | 93 | 17 (Računari parent) |

Šest gornjih = isti uzrok: 125 je curated bucket. "Desktop Brand Name"
je drugačiji — leaf 93 nije u Claude enum-u pa Claude ide na parent 17.

### Cluster B — NULL routing (17 fails)

Claude **ne pošalje** `category_id` za doslovni match imena kategorije.
Najjači znak da Claude ne prepoznaje upit kao kategorijski:

- "HDD storage", "Optika interna", "Graficke kartice", "Napojne jedinice",
  "Zvucne kartice", "Skeneri", "Stabilizatori, regulatori", "Audio
  adapteri", "Kucna kina, player-i", "Rezervni dijelovi elektronika",
  "Printeri i skeneri" itd.

Nijedna od ovih kategorija (114, 116, 117, 120, 121, 131, 133, 142, 164,
167, 97...) NIJE u `categories.json` enum-u. Claude doslovno nema ID na
koji bi rutao, pa pusti `category_id=null` i osloni se na embedding.

Embedding RAG ponekad uhvati pravu kategoriju (4 od 17 NULL upita završi
sa `result_verdict=PASS` — "Ventilatori", "Napojne jedinice", "Baterije
za UPS", "Inverteri"). Ostalih 13 ne uhvati ni embedding.

### Cluster C — WRONG_TOOL (3 fails)

| query | expected leaf | routed parent | tool |
|---|---|---|---|
| Kablovi | 123 | 356 (Kablovi i adapteri) | category_overview |
| UPS | 132 | 94 (UPS, stabilizatori) | category_overview |
| Televizori | 163 | 148 (Televizori i prateća oprema) | category_overview |

Claude bira parent + overview jer leaf nije u enum-u (123 nije u 50;
148, 94, 356 jesu parent kategorije iz `categories_new.json`). UX je
možda OK (chip breakdown), ali eval ga označava FAIL jer expected je
leaf + search_products.

### Cluster D — EXACT_PARENT routing OK, result FAIL (2 fails)

| query | cat | n_returned | subtree_total |
|---|---|---|---|
| Matične ploče | 108 | 0 | 16 |
| Nosaci i stalci za TV | 165 | 0 | 76 |

Claude šalje pravi ID, hard filter aktivan, ali search vraća 0
proizvoda. To znači embedding score je previše agresivno odsijecan ili
postoji bug u kombinaciji `category_id` + buffer_mult. Treba zasebno
debug-ovati.

## Failure cluster (products run 07:15)

| query | tip | uzrok |
|---|---|---|
| "Dell laptop" | NULL routing | Claude nije poslao cat=98 ni brand=Dell (samo embedding) |
| "Sony TV" | EXACT_PARENT + result FAIL | routing OK (163), ali subtree_total=68 a vraća 5 mimo subtree-a |
| "namještaj" | NEG_REGRESSION | trebao bi escalate_to_human, Claude pokušao overview na cat 372 |
| "auto akumulator" | NEG_REGRESSION | isto — out-of-catalog upit, Claude pokušao search |

Prva dva su rješiva preko popravke enum-a. Druga dva su safety net
problem (kartica `tst1` u Todo) — Claude ne prepoznaje out-of-catalog
upite konzistentno.

## Korak-po-korak preporuke

### Korak 1 — Završi migraciju ka `categories_new.json` (single source of truth)

Najveći ROI. Pokriva Cluster A (7 fails) + dio Cluster B (NULL ima
katastrofu jer Claude nema ID). Već je polu-migracija — `category_overview`
gleda u `categories_new.json`, ali `search_products` ne. Treba završiti.

**Konkretno (bez .env)**: refactor `app/tools.py` tako da i
`_load_categories()` čita iz `categories_new.json` (ne više iz
`categories.json`). Funkcija vraća `{cid: {label, count, examples}}` za
sve `status=1` kategorije. Labele dolaze iz `categories_new.json` (h1_title
ili name); count se izračuna iz `data/all-products.json`; examples se
generišu lazy (prvi 3 imena proizvoda).

**.env nije pravo mjesto** — to je config za flag-ove (effort, backend,
URL-ovi), ne za podatke. Hijerarhija od 255 kategorija ne ide u env var.
Pravo "single source of truth" rješenje: jedan canonical fajl
(`categories_new.json`) + sve ostale derivacije se rade u memoriji
(enum + label-i + parent expansion mapa) iz tog jednog fajla. To znači:

- `_CATEGORY_IDS` (enum za `search_products`) — iz `categories_new.json`.
- `_PARENT_CAT_IDS` (enum za `category_overview`) — već iz
  `categories_new.json`, ostaje.
- `_cat_descendants` u `rag.py` — premjesti iz `categories.csv` u
  `categories_new.json` (ima `parent_id` polje, dovoljno). CSV postaje
  legacy import-only artifact za jednokratne re-builde.

**Edge case**: enum od 255 ID-jeva napuhne tool schema. Anthropic
prihvata duge enum-e ali tool description ima soft limit ~16-20KB. Ako
tool description postane > 8000 tokena, grupiši `_CATEGORIES_BLOCK` po
parent-u (već koristi parent_id) — Claude vidi hijerarhiju umjesto flat
listu. Token cost mjeri u `evals/runs/` HTML-u prije i posle.

**Migracija po koracima** (svaki commit zaseban):
1. Napiši `_load_categories_from_new()` u `app/tools.py` koja vraća isti
   shape ({cid: {label, count}}) ali iz `categories_new.json`.
2. Pusti pored postojećeg `_load_categories()`. Feature flag u
   `app/config.py` (`USE_CATEGORIES_V2 = bool` default `false`).
3. Smoke run u kontrolnom okruženju sa flag=true. Ako PASS rate ide
   gore, flip default. Stari `categories.json` ostaje read-only do
   sljedeće release.
4. Tek nakon stabilizacije: ukloni `_load_categories()` i
   `data/categories.json`.

Procjena: 4-6h (skripta + feature flag + smoke run + token cost
benchmark + diff izvještaj).

### Korak 2 — Cluster D bug (search vraća 0 sa hard cat filter)

Reproduciraj lokalno sa `category_id=108` i upit "Matične ploče".
Buffer_mult je 8 sa hard filter-om (rag.py:424), znači sprema 8*top_k =
80 kandidata u buffer prije filter-a. Ako u tih 80 nema 16 proizvoda iz
cat 108, problem je u embedding score-u prije filter-a.

Pretpostavka: query "Matične ploče" je generička, embedding je rasut po
cijelom katalogu, top 80 ne uhvati nijedan iz cat 108. Treba category
boost koji se aktivira **prije** hard filter-a (sad se aktivira samo
kad `category_id is None`).

Procjena: 1-2h debug + 1h fix.

### Korak 3 — System prompt nudge protiv NULL routing

Cluster B ostatak (13 fails koje ni embedding ne uhvati): Claude ne
zove tool sa category_id za upit koji je doslovno ime kategorije.
Dodati few-shot u `app/system_prompts.py`:

```
"HDD storage" → search_products(category_id=114)  # tačan match imena
"Skeneri" → search_products(category_id=131)
"Graficke kartice" → search_products(category_id=117)
```

Ovo se mora uraditi POSLE Koraka 1 (nema smisla u prompt-u referencirati
ID-jeve koji nisu u enum-u).

Procjena: 1h prompt edit + smoke run.

### Korak 4 — Cluster C semantika u eval-u

Sada eval kaže WRONG_TOOL kad Claude pravilno bira category_overview za
nejednoznačan upit ("Kablovi" — može biti USB, video, mrežni). Treba
odlučiti: da li je overview validan kad expected je search_products na
leaf-u?

Opcija 1: eval prihvata overview kao validan **ako** routed parent je
ancestor expected leaf-a. To bi pretvorilo 3 WRONG_TOOL u PASS bez
gubljenja signala.

Opcija 2: eval set se proširi sa `expected_tool: search_products OR
category_overview` polje.

Diskusija sa korisnikom prije izmjene eval shema.

Procjena: 1h (uz odluku).

### Korak 5 — Negative regression (Cluster products D-1, D-2)

"namještaj" i "auto akumulator" — Claude treba escalate, ne search.
Kartica `tst1` ("Safety net + edge case-ovi") već pokriva ovo. Konkretni
fix: u system prompt-u explicit lista out-of-catalog kategorija +
escalate trigger-i. Vezano za eval set proširenje sa real out-of-catalog
upitima (već je 7 takvih u `products_cold.json` po brojanju iz STATUS-a).

Procjena: 0.5 dan (već u tst1 scope-u, ne odvojeno).

## Predloženi redoslijed

1. **Korak 1 prvo** (najveći ROI, eliminiše Cluster A + omogućava
   Korak 3 + djelimično Cluster C jer Claude će imati leaf cat-ove pa
   neće bježati na parent overview).
2. Re-pokreni smoke posle Koraka 1 — vidi koliko clusters preživi.
3. Onda Korak 2 (Cluster D) i Korak 3 (NULL nudge) zajedno.
4. Korak 4 (eval semantika) zadnji — možda postane non-issue nakon 1+3.
5. Korak 5 (safety net) ide pod kartica `tst1`, ne pod ovu analizu.

Očekivanje: nakon Koraka 1-3 trebalo bi pasti sa 29 FAIL na ≤10 FAIL
u categories run-u. Korak 4 može oboriti do 5-7. Korak 5 je za products
negativni put.

## Što nije u scope-u ove analize

- Sinoćnja server flakiness (HTTP 503 / ReadError) — već popravljen
  truncation u eval skripti (commit `ce692ab`); sljedeći put kad se
  reprodukuje, HTML će pokazati pun `internal_type`.
- Multi-turn eval set (`multi_turn.json` u kartici `evf2`) — odložen.
- Pre-router skica (deterministic layer ispred Claude-a) — kartica
  `evf2` "Ostaje" tačka 5, odloženo do nakon baseline-a.

## Bilješka o kartici `phir` (Hijerarhijske kategorije)

Kartica `phir` u Todo (`Hijerarhijske kategorije — parent_id u AI
pretrazi`) je djelimično implementirana kroz `category_overview` tool
(parent-child preko `categories_new.json`) i `_load_cat_descendants`
(parent expansion u hard filter-u preko `categories.csv`). Šta NIJE
urađeno i šta ova analiza dodaje:

1. **Single source of truth** — sva tri data fajla i dalje koegzistiraju
   (vidi Root cause tabelu). Korak 1 u ovoj analizi je konkretan plan da
   se to riješi.
2. **`search_products` enum migracija** — najvažniji nepokriven dio
   kartice `phir`; popunjava se Korakom 1.
3. **Drift dokumentacije** — kartica `phir` tačka 4 traži da
   `docs/features/ai-search-improvements.md` se ažurira sa hijerarhijom.
   Ne mijenjam ovdje (samo nalaz), ali kartica `phir` opis treba
   dopuniti referenciranjem ovog .md fajla.
