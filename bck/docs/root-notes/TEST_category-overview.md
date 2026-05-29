# TEST: Category overview tool (covt)

Manualni DoD test za `category_overview` tool (task **covt** u STATUS.md).
Provjerava da li Claude, kad korisnik kuca SAMO ime parent kategorije
("Mobiteli", "Računari", "TV"), poziva novi tool sa breakdown-om po
direktnoj djeci umjesto da gađa proizvode iz nasumičnog leaf-a kroz
`search_products`.

Tehnička referenca + ASCII tok pretrage:
[`docs/features/category-routing.md`](docs/features/category-routing.md).

## Kako pokrenuti

```bash
# 1. Restart uvicorn (uvicorn --reload prati .py ali ne .env, a tool se
#    učitava pri importu modula — bezbjedno restartovati)
pkill -f "uvicorn app.main" || true
.venv/bin/uvicorn app.main:app --reload --port 7778 &
# Sačekaj ~5s da boot-uje (prvi /api/chat poziv pokreće RAG index load
# dodatnih ~50s).

# 2. Smoke test — parent upit
curl -sS --max-time 180 -X POST http://127.0.0.1:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Mobiteli","session_id":"smoke-overview"}' | jq .

# 3. Kontra-test — upit sa kvalifikatorom (treba `search_products`, NE
#    `category_overview`)
curl -sS --max-time 180 -X POST http://127.0.0.1:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"iPhone 16","session_id":"smoke-overview-2"}' | jq .
```

## Šta očekuješ — PASS scenario

### Test 1 — "Mobiteli" (parent upit bez kvalifikatora)

**`tools_used` u responseu:** sadrži `"category_overview"` (NE
`"search_products"`).

**`reply` sadrži ova 3 chip-a (redom po sort_id):**

| Chip | Count | Top 3 primjeri (početak imena) |
|---|---:|---|
| 📂 **Mobilni telefoni** | 165 | Apple iPhone 13 128GB Black, … Starlight, … 14 128GB Black |
| 📂 **Dodaci za mobitele** | 129 | AUTO DRŽAČ CH04 …, Auto Punjač za mobitel …, BOROFONE BH203 … |
| 📂 **Maske za mobitele i dodaci** | 1274 | (start sa AKRILNO LJEPILO / ZAŠTITNA MASKA …) |

**Završna rečenica:** poziv korisniku da kaže model/brend/budžet
("Recite koji vas zanima …").

**Šta NE smije biti:**
- Lista product cards sa cijenama i slikama (overview je navigacijski,
  ne product listing)
- `---` horizontal rule između chip-ova
- Markdown tabela sa proizvodima
- Cijene proizvoda u top3 primjerima
- Nepostojeći proizvodi (halucinacija)

### Test 2 — "iPhone 16" (upit sa kvalifikatorom)

**`tools_used` u responseu:** sadrži `"search_products"` (NE
`"category_overview"`), sa `category_id="175"` (Mobilni telefoni) i
po mogućnosti `brand_id="APPLE"`.

**`reply` je standardna lista product cards** u jednom redu po proizvodu
(slika — ime — cijena — dostupnost — link).

### Test 3 — ostale parent kategorije (opciono)

Probaj redom: "Računari", "TV", "Bijela tehnika", "Printeri", "PC
komponente". Svaka treba pozvati `category_overview` sa odgovarajućim
`cat_id`. Mapa:

| Upit | Očekivani `cat_id` | # djece | Najveće dijete |
|---|---:|---:|---|
| "Mobiteli" | 151 | 3 | 394 Maske (1274) |
| "Računari" | 17 | 11 | 99 Tablet (57) ili 289 Dodaci za tablet (50) |
| "TV" / "Televizori i prateća oprema" | 148 | 6 | 165 Nosaci za TV (76) ili 163 Televizori (68) |
| "Printeri" / "Printeri i skeneri" | 97 | 7 | 127 Multifunkcijski (10) |
| "PC komponente" | 107 | 16 | 118 Kućišta (58), 111 CPU coolers (33) |
| "PC periferija" | 219 | 19 | 221 Slušalice (284) |
| "Bijela tehnika" / "Kućanski aparati i bijela tehnika" | 296 | 5 | (zavisi od indeksa) |

## Brzi check bez servera (statički)

Ako ne želiš da pališ uvicorn, handler se može pozvati direktno:

```bash
.venv/bin/python -c "
import json
from app.tools import handle_category_overview, PARENT_CATEGORIES
print('Parents:', len(PARENT_CATEGORIES))
r = json.loads(handle_category_overview('151'))
print(f\"{r['parent_label']} ({r['parent_id']}):\")
for ch in r['children']:
    print(f\"  {ch['cat_id']} {ch['label']:35s} count={ch['count']}\")
    for p in ch['top3']:
        print(f\"     {p['name'][:60]}\")
"
```

Očekivani output (zadnja provjera 2026-05-22):

```
Parents: 26
Mobiteli (151):
  175 Mobilni telefoni                    count=165
     Apple iPhone 13 128GB Black
     Apple iPhone 13 128GB Starlight
     Apple iPhone 14 128GB Black
  176 Dodaci za mobitele                  count=129
     AUTO DRŽAČ CH04 ZA KONTROLNU PLOČU
     Auto Punjač za mobitel Tel1 2xUSB 2A WHITE + MicroUSB cable
     BOROFONE AUTO DRŽAČ BH203 BLUE CHARM SA INDUKCIJSKIM PUNJENJ
  394 Maske za mobitele i dodaci          count=1274
     AKRILNO LJEPILO OD KALJENOG STAKLA ZA APPLE WATCH 4/5/6/SE 4
     ...
```

## Često viđene greške

| Simptom | Vjerovatan uzrok | Fix |
|---|---|---|
| `tools_used` = `["search_products"]` umjesto `["category_overview"]` | System prompt nudge nije pokupljen (uvicorn stari proces) ili Claude trenutno preferira search | Restart uvicorn. Ako i poslije toga Claude bira search, ojačaj 1b u `app/system_prompts.py` (npr. eksplicitno listiraj sve 26 parent imena) |
| Response sadrži cijene i product cards | Claude koristi overview rezultat ali ga renderuje kao search-style listu | Pojačaj FORMAT sekciju u `system_prompts.py` (overview = navigacija, NE product cards) |
| Handler vraća "Nepoznat parent cat_id" | Claude poslao cat_id koji nije parent (npr. 175 umjesto 151) | Ovo je tool-level greška — Claude treba samo da bira iz enum-a; ako se pojavljuje, provjeri da li je `_PARENT_CAT_IDS` ispravno učitan |
| Prazan `top3` za neko dijete (count > 0) | Mismatch između `_idx_to_cat` i `_products` mape | Provjeri `products.meta.json` integritet — `categories_id` polje mora se poklapati sa `categories_new.json` ID-ovima |
| HTTP 500 na `/api/chat` | Tool register grananje u `agent.py` ne prepoznaje novo ime | Verifikuj da je `category_overview` u `_HANDLERS` mapi i u `ALL_TOOLS` listi (`tools.py`) |

## DoD kriterijum

Test se smatra **prošlim** ako:

1. Test 1 ("Mobiteli") — `tools_used` sadrži `"category_overview"` i NE
   sadrži `"search_products"`. Response sadrži imena sva 3 chipa
   (Mobilni telefoni / Dodaci / Maske) sa pripadajućim count brojevima.
2. Test 2 ("iPhone 16") — `tools_used` sadrži `"search_products"` i NE
   sadrži `"category_overview"`. Response je product card lista.
3. Statički test (`.venv/bin/python -c …`) izlazi sa očekivanim brojevima
   (165/129/1274 za 151).

Ako bilo koji od ova tri padne — vidi tabelu "Često viđene greške" iznad.
