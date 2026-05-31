# AI Search Improvements — Brand awareness + proširene kategorije

**Branch:** `feature/ai-search-brand-category-improvements`
**Datum:** 2026-05-08

> **⚠️ Istorijski doc — superseded.** Ovaj dokument opisuje stanje od
> 2026-05-08 kada su kategorije bile podijeljene u 3 paralelna fajla
> (`categories.json`, `categories.csv`, `categories_new.json`). Sistem
> je 2026-05-23 prešao na **single source of truth** preko
> `app/categories.py` modula koji učitava taxonomy iz jednog fajla i
> izlaže sve derivacije. Vidi:
> - [`SSOT-categories-refactor-plan.md`](../../SSOT-categories-refactor-plan.md)
> - [`category-routing.md`](./category-routing.md) (osvježen post-SSOT)
>
> Tehnike opisane ispod (brand detection, soft boost, bidirectional prefix
> match) i dalje važe — ali svako pominjanje `categories.csv` ili
> `categories.json` zamijeniti mentalno sa `app/categories.py` SSOT-om.

Cilj: napraviti najbolju AI pretragu webshop-a u Banjaluci/RS. Iskoristiti dva
nova izvora podataka (`data/brend.json`, `data/categories.csv`) koje smo dobili
iz phpMyAdmin export-a webshop baze, pa proširiti pokrivenost klasifikacije
upita i dodati brand-aware ranking koji prije nije postojao.

---

## Šta se mijenja

### 1. `data/category_terms.json` — automatska generacija iz CSV-a

**Prije:** 13 ručno upisanih kategorija sa ~50 termina ukupno.

**Sad:** 89 kategorija sa ~500 termina, izvor SEO `meta_keywords` u
`categories.csv` plus manual override layer za migration drift i BCS
skraćenice (`tv`, `mb`, `kompjuter`).

Kako radi:
- `scripts/build_category_terms.py` čita `data/categories.csv`,
  parsira `meta_keywords` (SEO-curirano polje, npr. *"RAM memorija, DDR4,
  DDR5, Kingston RAM, ..."*), filtrira SEO šum (BiH, online, kupite,
  povoljno) i imena brendova kao single-token (Apple sam, ASUS sam — ti
  pripadaju brand-detection sloju).
- Drop kategorija sa <5 proizvoda u indeksu — to su "migration ghost"
  cat-ovi gdje je CSV taxonomy novija od product snapshot-a (npr. cat 148
  "Televizori i prateća oprema" ima 1 proizvod, a stvarni TV-i su u cat 163
  sa 67 proizvoda).
- Manual override layer (`MANUAL_TERM_ADDITIONS` u skripti) dodaje BCS
  skraćenice koje SEO ne uključuje, plus drift target-e (cat 277 "Ostalo"
  zapravo je 535 proizvoda od kojih je 45% miševa — ručno dodajemo `miš`,
  `mis`, `miševi`).

**Regeneracija:** `python scripts/build_category_terms.py` (par sekundi).
Search-time boost u `app/rag.py` odmah koristi novu listu.

**Embedding refresh (opciono):** `python scripts/embed_products.py`
(~5 min) ako želimo da se prefix-i također ugrade u indeks (3x repetition
mehanizam u `build_search_text`).

### 2. `data/categories.json` — proširena na top 50 + CSV labels

**Prije:** Top 30 kategorija, ručno labeliranih u `LABELS` dict u
`build_categories.py`. Auto-fallback za nove kategorije.

**Sad:** Top 50 kategorija (90.5% pokrivenosti kataloga vs prethodnih 30).
Labele dolaze iz `categories.csv` (`h1_title` polje), uz `LABEL_OVERRIDES`
za 11 slučajeva gdje CSV name nije dovoljno jasan ili zbog migration drift-a
(cat 277 → "Miševi i razni PC dodaci" jer CSV name kaže "Ostalo").

### 3. `app/rag.py` — brand awareness + bidirectional prefix match

**Brand detection** (novo):
- Učitava `data/brend.json` (90 brendova, neki imaju `priority` 1–20 za
  top-tier).
- Detektuje brand mention u query-ju kroz token + bigram match (Apple,
  ASUS, "cooler master", "western digital").
- Single-token blocklist (`cooler`, `western`, `lipa`, `max`...) sprečava
  da generičke riječi triggeruju brand boost (npr. "cpu cooler" ne
  detektuje COOLER MASTER — trebao bi zaista biti taj brand u upitu).

**Boost logika** (proširena):
- `category_id` (od AI-ja) → hard filter na `categories_id`. Postojalo.
- `brand_id` (od AI-ja, NOVO) → hard filter na `id_brend`. Kombinovano
  sa `category_id` daje precizan filter ("Apple iPhone" → cat=mobiteli,
  brand=APPLE).
- Bez hard filtera: detect both intent_cats and intent_brands, primijeni
  +0.25 boost svakom (kumulativno do +0.5).
- Tie-breaker: brand priority 1–20 razrješava skoro-iste rezultate u
  korist popularnih brendova.

**Bidirectional prefix match** (novo):
- Stari kod: term mora biti prefix tokena (laptop → laptopa). Riješava
  BCS deklinaciju.
- Novi kod: dodatno token može biti prefix terma (monitor → monitori).
  Riješava singular query vs plural CSV term ("monitor 27\"" sad
  match-uje term "monitori").

**Head-noun fallback** (novo):
- Stari kod: ako prvi non-stop token ne match-uje, ne traži dalje.
- Novi kod: ako prvi ne match-uje, probaj drugi, treći. Stop na prvom
  match-u (zadržava "miš za laptop" → cat 277, ne 98). Riješava:
  - "samsung tv" — "samsung" je brand (filtriran iz cat terms),
    "tv" → cat 163 ✓
  - "gaming miš" — "gaming" je modifier, "miš" → cat 277 ✓

### 4. `app/tools.py` — `brand_id` u tool schema

`search_products` sada prima opcioni `brand_id` (enum-iran iz brend.json).
AI sees:
- Lista 90 brendova u opisu tool-a (sortirano po priority — Apple, ASUS,
  Canon, Dell, Epson... pa ostalo abecedno).
- Pravila klasifikacije: brand-only, brand+kategorija, brand+model.

Token cost: ~500 tokena više po request-u (svi brendovi). Cijena
pri Sonnet rate-u: ~$0.0015 dodatno po pozivu.

---

## Kako testirati

### Pokreni testove

```bash
source .venv/bin/activate
pytest tests/test_brand_category_search.py -v
```

29 test-ova pokriva:
- `TestCategoryTermsData` — struktura i pokrivenost terma
- `TestBrandData` — top brendovi prisutni i sortirani
- `TestBrandDetection` — detection iz query-ja
- `TestCategoryDetection` — head-noun fallback, BCS singular/plural
- `TestBrandSearch` — hard filter end-to-end
- `TestRegression` — postojeće funkcionalnosti netaknute

### Manuelni smoke test sa prave webshop instance

Pokreni server lokalno:

```bash
uvicorn app.main:app --reload
```

Otvori `http://localhost:8000` (chat widget) ili curl direktno
`/api/chat`. Probaj sledeće upite i provjeri:

| Upit | Očekivani brand_id | Očekivani category_id | Šta gledamo |
|---|---|---|---|
| `Apple iPhone` | 11 (APPLE) | 175 (Mobiteli) | Najnoviji iPhone modeli prvi |
| `samsung tv` | 68 (SAMSUNG) | 163 (Televizori) | Samsung 4K, OLED prvi |
| `asus laptop do 1500 KM` | 13 (ASUS) | 98 (Notebook) | Asus Vivobook, Zenbook ≤1500 KM |
| `gaming miš` | — | 277 (drift target) | Logitech, Razer gaming miševi |
| `mis za office` | — | 277 | Miševi (ne torbe za laptop) |
| `kabal hdmi 2m` | — | 137 (USB i data kablovi) | HDMI kablovi |
| `western digital ssd 1tb` | 86 (WD) | 115 (SSD storage) | WD SSD modeli |
| `cooler master case` | 20 (COOLER MASTER) | 118 (Kućišta) | CM kućišta |
| `cpu cooler` | — | 111 (CPU cooler-i) | Hladnjaci za procesor (NE Cooler Master kućišta) |
| `tv` | — | 163 | Svi TV-i |
| `mb intel z690` | 42 (INTEL) | 108 (Matične ploče) | Z690 matične |
| `iPhone 15 Pro` | — (AI će dodati 11) | 175 | Konkretan model |
| `tableti za djecu` | — | 99 (Tableti) | Tableti, ne dodaci |
| `powerbank` | — | 202 | Power bank-ovi |
| `gift card playstation` | — | 393 | PS gift kartice |

Edge case-ovi za potvrdu da nismo zalomili:

| Upit | Šta očekujemo | Razlog |
|---|---|---|
| `mis za laptop` | Cat 277 boost, NE 98 | head-noun je "miš", ne "laptop" |
| `lipa mill papir` | brand=50 (LIPA MILL) | Multi-token brand match |
| `lipa` (sam) | nema brand | "lipa" sam u blocklisti — too generic |
| `cooler za procesor` | cat 111, NE brand 20 | "cooler" sam ne znači COOLER MASTER |
| `najbolji laptop do 1500 KM` | cat 17 + 98 | Long query, ali pod prag od 4 non-stop |
| `trebam mali laptop za firmu sa dobrom baterijom` | nema cat boost | >4 non-stop tokena, isključuje boost |

### A/B test plan (sledećih dana)

Da odlučimo da li je pobjeda realna, ne samo subjektivna:

1. **Skupi baseline upite** — top 50 stvarnih korisničkih upita iz dashboard-a
   (ako nemamo evals/, izvuci iz `var/sessions.db` poslije par dana
   prometa).
2. **Snimi rezultate prije i poslije** za isti set upita. Trenutni
   `evals/` framework treba da se dopuni novim test setom.
3. **Mjeri**:
   - Click-through rate na top-3 rezultata (da li korisnik klikne).
   - Recall za nišne upite (gaming miš, lipa mill, mb z690).
   - Hallucination rate (AI tvrdi da nemamo X iako imamo).

---

## Decision point: JSON schema + examples vs trenutni enum + label

User feedback poziva na odluku u sledećih par dana. Evo trade-off-a kako
bismo objektivno odlučili:

### Option A — TRENUTNI: enum + label list u tool description

Šta to znači:
- Tool `search_products` ima `category_id: enum [50 IDs]` + opis sa
  punim listom `cat_id: label`.
- Nakon ovog branch-a: dodaje se `brand_id: enum [90 IDs]` + lista
  brendova u opisu.
- AI vidi sve labele u svakom request-u, bira slobodno.

**Plus:**
- Zero hallucination cat_id-a — enum garantuje validnost.
- Single-call: AI klasifikuje + bira tool atomski (jedan LLM round-trip).
- Uzbeko da implementiramo, već radi.
- Lako za maintain — promijeniš `categories.csv` ili `LABEL_OVERRIDES`,
  regenerišeš JSON.

**Minus:**
- Token cost po request-u: ~600 (cats) + ~500 (brands) = ~1100 dodatnih
  input tokena svakog put. Pri 10k requesta dnevno: ~11M tokena/dan
  premium. Sonnet input rate je ~$3/MTok → ~$33/dan, $1k/mjesec.
- Redundantno informisan AI: ako pita za "iPhone", svejedno vidi listu
  od 50 cat-ova kojih većina nikad neće biti relevantna.
- Skaliranje: ako dodamo još brendova ili kategorija, prompt raste linearno.

### Option B — JSON SCHEMA + EXAMPLES (alternativa)

Šta to znači:
- Tool description ima 5–10 PRIMJERA validnih klasifikacija
  (`"Apple iPhone" → cat=175, brand=11`), ne punu listu.
- Schema definiše `category_id` i `brand_id` kao **string** bez enum-a.
- AI mora generisati validan ID iz znanja + primjera.

**Plus:**
- Drastičan pad token cost-a: ~200 tokena umjesto 1100. Mjesečno: ~$200
  uštede.
- AI generališe bolje na nove brendove/kategorije bez retrain-a.
- Manje "buke" u promptu — AI se fokusira na semantiku upita, ne na
  scrolling kroz 90 brand-ova.

**Minus:**
- **Hallucination risk**: AI može da izmisli cat_id (npr. "176" za
  laptop kad cat 176 nije laptop). Validation post-hoc: ako AI vrati
  nepostojeći ID, fallback-uj na pretragu bez filtera (degradacija
  graceful).
- Recall za rijetke kategorije pada: ako "rezači papira" nisu u
  primjeru, AI neće znati za cat ID. Trebalo bi dodati 2-step pristup
  (tool `classify_query` → `search_products`).
- Više engineering-a: validation layer, eval framework za hallucination
  rate, primjer-curiranje.

### Hybrid (Option C)

- Kategorije: top 10 u opisu, ostalo dostupno preko `lookup_category`
  tool-a kad AI ne zna ID.
- Brendovi: priority 1–20 u opisu, ostalo via lookup.

Token cost ~300 (vs 1100) sa 90% recall za top upite, lookup tool za rep.
Razvojni overhead: medium (treba dodati lookup tool + protokol).

### Predlog odluke

**Predlažem da ostanemo na Option A za prvih 2–4 sedmice produkcije**, dok
ne sakupimo:
1. Stvarni token cost iz dashboard logging-a.
2. Distribuciju upita po kategorijama — koliko je "long tail" zaista bitan?
3. Hallucination baseline (ako koristimo schema bez enum-a, mjerimo
   ručno na 50 upita).

Ako mjesečni cost > $200 ili ako vidimo da 80% upita ide u top 15 cat-ova,
**Option C (Hybrid)** je sledeći korak. Option B čistim primjerima je
preriskantno za production bez prethodnog eval framework-a.

---

## Future work

- **Hierarhijska expansion**: parent_id u CSV-u nudi tree (cat 17 → 93,
  98, 99 children). Zbog migration drift-a (parent ima 18 proizvoda, child
  93 ima 0), naivna ekspanzija boost-uje ghost cats. Da bi imala vrijednost,
  treba post-process: drop deprecated children, mapirati drift target-e
  ručno. Vrijedno tek poslije clean-up-a kataloga.
- **Reindex sa novim category_terms**: trenutno samo search-time boost
  koristi novi `category_terms.json`. Za maksimalnu pobjedu (embeddings
  + BM25 corpus), pokreni `python scripts/embed_products.py` (~5 min).
  Nakon prvog merge-a, dogovoriti se na CI-u kad reindex pada.
- **Brand priority kao default sort signal**: trenutno je tie-breaker za
  near-equal scores. Mogli bismo da ga koristimo i kao slabi soft sort
  za ravnopravne neutralne upite ("imate li nešto za firmu?").
- **iPhone → Apple inference**: trenutno "iPhone 15 Pro" ne hvata Apple
  brand sam (nije u brand keys). Mogli bismo da dodamo product-line
  aliase (iPhone → APPLE, Galaxy → SAMSUNG) ako se isplati.

---

## Fajlovi izmijenjeni

- `app/rag.py` — brand load + detection + boost + bidirectional prefix +
  head-noun fallback
- `app/tools.py` — `brand_id` u SEARCH_PRODUCTS tool schema, BRANDS load
- `data/category_terms.json` — REGENERISAN, 89 cats sa 500 termina
- `data/categories.json` — REGENERISAN, top 50 sa CSV labels
- `data/brend.json` — NOVI, phpMyAdmin export brendova (90 brendova)
- `data/categories.csv` — NOVI, phpMyAdmin export kategorija (255 redova)
- `scripts/build_category_terms.py` — NOVI generator
- `scripts/build_categories.py` — proširen sa CSV labels
- `tests/test_brand_category_search.py` — NOVI, 29 test-ova
- `docs/features/ai-search-improvements.md` — ovaj dokument

---

## Brzi reference za reviewer-a

```bash
# Regeneriši data fajlove (par sekundi)
python scripts/build_category_terms.py
python scripts/build_categories.py

# Pokreni testove (~60 sekundi prvi put zbog model load-a)
pytest tests/test_brand_category_search.py -v

# Probaj search ručno
python -c "
from app.rag import get_index
idx = get_index()
print(idx._detect_intent_brands('apple iphone'))
print(idx._detect_intent_categories('gaming miš'))
"

# Pokreni server za browser smoke test
uvicorn app.main:app --reload
```
