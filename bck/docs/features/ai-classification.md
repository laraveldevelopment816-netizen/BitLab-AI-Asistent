# AI klasifikacija namjere

> Kako AI razumije korisnikov upit, klasifikuje ga u kategoriju, i radi pretragu.

## Problem

Korisnici nisu uvijek precizni:
- "trebam nešto za kucanje" → **tastatura** (cat 220), ali "kucanje" nije u imenu nijednog proizvoda
- "imate li lapatovoe" → **laptop** sa typoom; embedding ne hvata "lapatovoe" kao laptop
- "treba mi disk za laptop" → **SSD/HDD** (cat 394 ili sl.), NE torba za laptop koja je accessory šum
- "samsung galaxy" — može biti telefon (cat 175) ILI tablet (cat 99)

Bez dobre klasifikacije, hibridni search vraća rezultate pomiješane sa accessory-jem (torbe, postolja) ili ne razumije sinonime.

## Rješenje — tri sloja

### Sloj 1 — AI klasifikacija namjere (primarno) ⭐

`data/categories.json` (generiše `scripts/build_categories.py`) sadrži **top 30 kategorija** sa human-readable labelama:

```json
{
  "98":  {"label": "Laptopi i notebook računari", "count": 50, "examples": [...]},
  "220": {"label": "Tastature", "count": 99, ...},
  "277": {"label": "Miševi", "count": 535, ...},
  "394": {"label": "Maske, futrole i zaštitna stakla za telefone", ...}
}
```

Kategorije pokrivaju **81.5%** kataloga (4.304 / 5.278 proizvoda).

Lista se utiskuje u `search_products` tool description **i** kao `enum` na `category_id` parametru — Claude vidi listu pri svakom pozivu i sam klasifikuje upit u jedan ID. Single-call flow:

```
korisnik: "trebam nešto za kucanje"
  ↓
Claude (jedan API poziv)
  → search_products(query="tastatura", category_id="220")
  ↓
rag.search() → hard filter na 99 tastatura, hibridni rang unutar
```

Pravilo u system prompt-u (`BITLAB_BASE` Pravilo 1a):

> **Klasifikacija namjere prije pretrage:** korisnici nisu uvijek precizni. Prije nego što pozoveš `search_products`, razumi šta korisnik zapravo traži i — ako je upit kategorijski — popuni `category_id` parametar.

Plus typo robustnost (`CHAT_FORMAT`):
- "lapatovoe", "laptopov" → laptop (cat 98)
- "tastruru", "tipkovnicu" → tastatura (cat 220)
- "monjitor" → monitor (cat 224)
- "telfon" → mobitel (cat 175)

### Sloj 2 — Build-time prefix (`data/category_terms.json`)

Mapiranje kategorija → terminima koji nisu u imenima proizvoda. U `embed_products.py` se prefix ponavlja 3× u `search_text` polju → embedding razumije "laptop" iako su u imenu samo brendovi (Acer Nitro, Lenovo IdeaPad).

Pomaže semantičkom retrieval-u **unutar** odabrane kategorije.

### Sloj 3 — Search-time soft boost (fallback)

Ako Claude **ne pošalje** `category_id` (npr. brand+model upit "Patriot SSD 240GB"), `rag.py` i dalje pokušava intent detekciju iz `category_terms.json` i daje **+0.25 boost** match-ed proizvodima — sprečava accessory šum.

Kad je `category_id` zadat, hard filter ima prednost i soft boost se preskače (jer je suvišan).

## Eval

**`evals/run_categories.py`** — 41 realni upit + očekivani `category_id`. Trenutni rezultat: **100%** (Sonnet 4.6) sa svih 5 typo case-ova.

**`evals/run_format.py`** — provjera RAW Claude output-a (bez backend strip-a) za markdown tabele, `---`, voice tag leak. Threshold 95%.

## Kad dodati novu kategoriju

1. Dopuni `LABELS` dict u `scripts/build_categories.py`
2. Pokreni `python scripts/build_categories.py`
3. Dodaj 1–2 reprezentativna upita u `evals/category_eval.json`
4. Pokreni `python evals/run_categories.py` — mora ostati ≥80%
5. (Opciono) Build-time prefix u `category_terms.json` ako embedding sam ne hvata kategoriju

## Implementacija

| Fajl | Šta radi |
|---|---|
| `scripts/build_categories.py` | Generiše `data/categories.json` iz `products.meta.json` |
| `app/tools.py` `SEARCH_PRODUCTS` | Tool schema sa `category_id` enum + lista u description |
| `app/rag.py` `search()` | Hard filter po `category_id`, soft boost fallback |
| `app/system_prompts.py` `BITLAB_BASE` Pravilo 1a + `CHAT_FORMAT` | Pravila za Claude-a |
| `data/categories.json` | Top 30 kategorija sa label + examples + count |
| `data/category_terms.json` | Build-time prefix + soft-boost mapiranje |
| `evals/category_eval.json` | 41 realni upit + očekivani cat_id |
| `evals/run_categories.py` | Eval runner, mjeri top-1 accuracy |
