# SSOT eval delta — 2026-05-23

Analiza poslednjih smoke run-ova pre i poslije SSOT refaktora:

| eval | pre-SSOT (07:02 / 07:15) | post-SSOT (11:59 / 11:34) | delta |
|---|---|---|---|
| categories (50q) | 21 PASS / 29 FAIL | 25 PASS / 23 FAIL | **+4 PASS / -6 FAIL** |
| products (21q) | 17 PASS / 4 FAIL | 12 PASS / 9 FAIL | **-5 PASS / +5 FAIL** |

Na prvi pogled products je regresija, ali kad se uđe u svaki padajući
slučaj — **SSOT je dobro implementiran**. Pravi uzroci su:

## Nalaz 1 — SSOT je riješio originalni root cause (cat 125 fantom)

Pre-SSOT je 7 printer upita rutiralo na fantom bucket 125. Post-SSOT:

| upit | pre-SSOT routed | post-SSOT routed |
|---|---|---|
| Laserski printeri | 125 (fantom) | 124 (pravi leaf) ✓ |
| Inkjet printeri | 125 (fantom) | 97 (parent) |
| Multifunkcijski printeri | 125 (fantom) | 127 (pravi leaf) ✓ |
| Kopir aparati | 125 (fantom) | 97 (parent) |
| Foto printeri | 125 (fantom) | 97 (parent) |
| Matricni printeri | 125 (fantom) | 97 (parent) |
| Skeneri | NULL | NULL (i dalje) |

5 od 7 printer rutiranja sad ide na realne taxonomy ID-eve (umjesto
halucinacije). Eval označava 4 od njih kao OUT jer Claude bira parent 97
umjesto specifičnog leaf-a (npr. 127 za Multifunkcijski) — ali to je
semantički ispravnije ponašanje (parent expansion vraća sve printer-e
iz subtree-a), samo je eval previše striktan.

## Nalaz 2 — Products "regresija" je eval parser bug, ne SSOT regresija

Sva tri ključna products FAIL-a ("Dell laptop", "Sony TV", "Samsung
mobitel") imaju **prave rezultate u Claude reply-ju** — eval parser ih
ne uhvata.

### 2a) Multi-turn "rezultati prikazani iznad"

`Dell laptop` (cat=98, brand=23, top_k=10):
- iter 1: search_products vrati 10 proizvoda (44ms)
- iter 2: Claude napiše narativan summary: *"Rezultati su već prikazani
  iznad — 10 Dell laptopa na lageru od 1.169 do 2.999 KM."*
- eval parser uzima ZADNJI reply, tamo nema product redova → `products=[]`,
  n_returned=0, FAIL.

Isti šablon: `Sony TV` (cat=163, brand=71). Tool vrati rezultate, Claude
napiše *"Pretraga je već dala sve dostupne Sony televizore — svih 5 modela
iz serije X77L prikazani su iznad."*

Fix: eval parser treba spojiti sve iter-replies, ne samo zadnji. Ili
gledati `tool_calls[].result` directly.

### 2b) Image URL sa space-om

`Samsung mobitel` reply sadrži 10 Samsung mobitela u urednom markdown
formatu, ALI image URL ima space u sebi:

```
![](https://webshop.bitlab.rs/img/67975c94e6f52Samsung Galaxy A16 5G.jpg)
```

`PROD_RE` regex u `evals/run_products.py:58-62` koristi `https?://\S+?`
(non-whitespace) za image URL match — puca na razmak. Sva 10 proizvoda
parsirani kao `products=[]`.

Fix: regex za image URL treba prihvatiti space (`[^\)]+?` umjesto
`\S+?`), ili tretirati image kao optional ne-greedy "do prvog `)` na
istom redu".

## Nalaz 3 — Drift problem (preegzistentan, izložen SSOT-om)

641 proizvod (~12% kataloga) "živi" u cat-ovima koji nisu u SSOT-ovom
ACTIVE_IDS:

| cat | proizvoda | status | name | in taxonomy |
|---|---|---|---|---|
| 277 | 535 | 0 | "Ostalo" | ✓ |
| 224 | 46 | 0 | "Monitori" | ✓ |
| 125 | 19 | — | (fantom) | ✗ |
| 395 | 16 | NULL | "4G ROUTERI" | ✓ |
| 290 | 11 | — | (fantom) | ✗ |
| ostali | 14 | — | — | mješano |

Posljedice u eval-u:
- `27 inch monitor` (expected cat=224): Claude ne vidi 224 u enumu →
  routed=None → embedding ipak vraća 10 proizvoda iz cat 224 (jer su
  products tako klasifikovani). result=PASS, ali routing=OUT → overall=FAIL.
- `gaming miš do 100 KM` (expected cat=277): isti šablon. result=PASS,
  routing=OUT.
- `HP printer` (expected cat=125): cat 125 ne postoji — i eval set ima
  zastarjeli expected_cat.

Ovo je drift IZMEĐU `products.meta.json` i `categories_new.json` — nije
SSOT bug, nego stari problem koji je SSOT izložio.

## Nalaz 4 — Stvarni preostali bug-ovi (nisu SSOT, kandidati za posebne kartice)

- **Cluster B NULL routing** smanjen sa 17 (pre-SSOT) na 9 (post-SSOT) —
  ali još uvijek ima 9 leaf cat-ova na koje Claude ne ruta čak iako su
  u enumu ("HDD storage", "Graficke kartice", "Skeneri", "Projektori",
  "Fiksna telefonija", "Kućišta", "Rezervni dijelovi elektronika",
  "Optika interna", "Produženje garancije"). Sistem prompt nudge je
  potreban (kartica `rtct`).

- **NEG_REGRESSION (3 fails)** — "namještaj", "biciklo", "gaming laptop
  do 100 KM" — Claude pokušava search/overview umjesto escalate. Safety
  net kartica `tst1`.

## Preporučeni redoslijed fix-eva (post-SSOT iteracije)

1. **Fix eval parser** (`evals/run_products.py:58-62` + zadnji-reply
   pretpostavka). Bez ovoga products eval je nepouzdan signal — ne
   možemo razlikovati pravu regresiju od parser bug-a.
2. **Odluka o drift cat-ovima** (277, 224): da li ih uključiti u SSOT
   (status=0 but in CATEGORIES) ili reklasifikovati 641 proizvod u
   aktivne cat-ove. Argumentacija u kartici `phir` (nije pokriveno u
   ovom SSOT refaktoru namjerno).
3. **Update eval set** — `products_cold.json` ima entry sa
   `expected_cat_id=125` (fantom) — treba zamijeniti sa realnim ID-jem.
4. **Sistem prompt nudge** (`app/system_prompts.py`) za NULL routing
   slučajeve — kartica `rtct` u STATUS-u.
5. **Negativni safety net** — kartica `tst1`.

## Zaključak o SSOT implementaciji

**Implementiran ispravno.** Svi key invariant-i drže:
- Cat 125 fantom eliminisan (potvrđeno: nije u CATEGORIES).
- `categories_new.json` referencirano samo na jednom mjestu
  (`app/categories.py:38`).
- `categories.csv` apsolutno uklonjen iz koda.
- Test parity prolazi 79/79 (kategorije, parent expansion, tools,
  brand-search, anthropic error handlers).
- Tool description token cost: 2464 → 5184 bytes (2.1×, manageable).
- 117 leaf cat-ova u enum-u umjesto 50 AI bucket-a — Claude sad vidi
  cijelu real taksonomiju za search_products.

**Apparentnu products regresiju** uzrokuju dva preegzistentna problema
(eval parser regex bug, parent-vs-leaf eval strictness) koji nisu bili
vidljivi ranije jer su mnogi upiti padali na drugi (sad eliminisan)
problem. Pravi product eval rezultati su **bolji** nego što izvještaj
pokazuje — Claude RADI tool calls, vraća prave rezultate, samo parser
ne uhvata.
