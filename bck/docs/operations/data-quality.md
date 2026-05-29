# Data quality

## Slike — 7.2% missing iz webshop CDN-a

### Problem

Webshop je migrirao image storage. Stari proizvodi sa kratkim cover prefiksom (npr. `728_lenovo.jpg`) imaju 302 redirect na homepage = slika ne postoji na CDN-u. Browser pokuša loadovati, dobije HTML, sakrije `<img>` kroz `onerror` — ali Claude svejedno generiše `![](url)` markup koji izgleda neuredno u raw output-u.

Audit (`scripts/audit_missing_images.py`) pokazao **374 / 5.177 = 7.2%** kataloga ima missing slike.

### Pattern

| Naming | Status | Primjer |
|---|---|---|
| **Modern** (7+ cifren prefix) | radi (200 OK) | `0141906_asus-e1504fa-bq1964-156-fhd-ag-60hz-amd-ryzen-3-7320u8gb512-gb-ssdcrna2y.png` |
| **Legacy** (kratak prefix) | 302 → homepage | `728_lenovo.jpg`, `45_x.jpg` |

### Fix u `rag.py`

`search()` postavlja `image_url=None` za:
- Cover sa legacy prefiksom (regex `^\d{7,}_` ne match)
- Sifre eksplicitno u `data/missing_images.json` (audit output)

Posljedica: Claude ne generiše `![](broken_url)` za te proizvode → product card prikazuje generičku ikonu umjesto razbijene slike.

### Audit refresh

```bash
python scripts/audit_missing_images.py --concurrency 50
```

~3 min za pun katalog (5.177 HEAD requestova). Output: `data/missing_images.json` sa listom svih missing.

Treba pokretati periodično (mjesečno) — webshop dodaje proizvode, neki se obrišu, neki se re-upload-uju.

## Kategorije — refresh kad se katalog promijeni

`data/categories.json` se generiše iz `data/products.meta.json`. Kad webshop doda nove proizvode ili promjeni kategorije:

```bash
# 1. Refresh meta iz webshop DB
python scripts/embed_products.py   # ~5 min, generiše products.index + meta

# 2. Regeneriši kategorije
python scripts/build_categories.py

# 3. Provjeri da nova kategorija nije fall-back na auto-label
# Ako jeste, dopuni LABELS dict u scripts/build_categories.py i ponovo pokreni

# 4. Eval da se uvjeriš
python evals/run_categories.py
```

Eval mora ostati ≥80% da deploy ne pokvari klasifikaciju.

## FAQ — `data/faq.md`

Ručno kuriran. Promjene:
1. Edituj `data/faq.md`
2. Restart `uvicorn` (FAQ se loaduje u memory pri prvom pozivu, cache-uje)
3. Nema audit — provjera se radi ručno kroz chat: "kakva je dostava?"

## Vector index — kad refresh-ovati

`data/products.index.npz` (5.278 vektora × 384 dim) se gradi iz `products.meta.json`. Treba refresh:
- Kad se promijeni `embed_model` u config-u (drugi sentence-transformer)
- Kad se promijeni `category_terms.json` (jer prefix utiče na search_text koji se embeduje)
- Kad webshop doda 100+ novih proizvoda (incremental refresh nije podržan, mora full rebuild)

Trajanje: ~5 min CPU + ~5 GB temp diska. Ne radi se na svaki deploy — samo kad podaci traže.

## SQLite DB — `var/bitlab.db`

Raste sa svakim chat upitom. Tabele:
- `requests` — ~500 bytes per row
- `tool_calls` — ~1-4 KB per row (output_text truncated 4KB)

Procjena: 1.000 chat-ova/mj × prosjek 3 tool calls = 4 MB / mjesec. Sporo raste.

**Backup strategija (TODO):**
```bash
sqlite3 /home/ai/aiasistent-prod/shared/var/bitlab.db \
  ".backup /home/ai/aiasistent-prod/shared/var/backups/bitlab-$(date +%F).db"
find /home/ai/aiasistent-prod/shared/var/backups -mtime +30 -delete
```

Cron jednom dnevno. Treba dodati u Sesiju 11.

## Kako inspect-ovati podatke

### Categories

```bash
python -c "
import json
d = json.load(open('data/categories.json'))
print(f'Top 30 kategorija ({sum(c[\"count\"] for c in d.values()):,} proizvoda)')
for cid, info in sorted(d.items(), key=lambda x: -x[1]['count'])[:10]:
    print(f'  {cid}: {info[\"label\"]:50s} {info[\"count\"]:>5}')
"
```

### Products meta

```bash
python -c "
import json
ps = json.load(open('data/products.meta.json'))['products']
print(f'Total: {len(ps):,}')
brand_count = {}
for p in ps.values():
    b = p.get('brand') or 'unknown'
    brand_count[b] = brand_count.get(b, 0) + 1
for b, c in sorted(brand_count.items(), key=lambda x: -x[1])[:10]:
    print(f'  {b:30s} {c:>5}')
"
```

### Missing images

```bash
python -c "
import json
d = json.load(open('data/missing_images.json'))
print(f'Provjereno: {d[\"checked\"]:,}')
print(f'Missing: {len(d[\"missing\"]):,}')
"
```

### Recent requests u DB

```bash
sqlite3 var/bitlab.db "
SELECT id, channel, model, status, latency_ms,
       substr(prompt, 1, 50) as prompt
FROM requests ORDER BY id DESC LIMIT 10
"
```

Ili pristupi kroz dashboard: `/admin/live`.
