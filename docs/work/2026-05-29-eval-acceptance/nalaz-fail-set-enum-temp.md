# Nalaz — fail-set run (enum + temperature)

**Datum:** 2026-06-05 · **Run:** `categories_acpt_fails` label `enum-temp`, PWR backend, `--no-cache`
**Izvor:** `evals/runs/categories_acpt_fails-enum-temp.jsonl` (23 slučaja = 15 padova zadnjeg punog runa + 8 negativaca)

## Rezultat: 14/23 PASS

Od 15 originalnih padova **8 je prešlo u PASS — tačno onih 8 leaf-kolizija**: model sada zove
`search_products` (leaf) umjesto `category_overview` (parent). **Izbor alata je riješen.** PWR nije
pukao na `temperature` uz `reasoning_effort` (taj caveat nije uhvatio).

## Zašto preostalih 7 (od 15) i dalje pada — NIJE više leaf/parent

| entry | upit | očekivano | model je pozvao | klasa |
|---|---|---|---|---|
| cat-leaf-186 | „Dodaci za telefone" | `search_products` cid=186 | `search_products` cid=**176** | pogrešan-ali-validan leaf |
| cat-leaf-274 | „Softver Aplikacije" | `search_products` cid=274 | `search_products` cid=**345** | pogrešan-ali-validan leaf |
| cat-leaf-329 | „Kućišta za HDD" | `search_products` cid=329 | `search_products` cid=**281** | pogrešan-ali-validan leaf |
| cat-leaf-204 | „Sony" | `search_products` cid=204 | `search_products` query+brand=Sony | brend-vs-kategorija (defanzibilno) |
| cat-leaf-112 | „Ventilatori" | `search_products` cid=112 | — (apstinencija) | dvosmislen upit |
| cat-leaf-245 | „Ventilatori" | `search_products` cid=245 | — (apstinencija) | dvosmislen upit |
| cat-leaf-253 | „Dodaci" | `search_products` cid=253 | — (apstinencija) | pregeneričko |

- **4 su pozvala TAČAN alat (`search_products`) ali pogrešan argument.** Tri su izabrala pogrešan
  ali **validan** leaf ID. **Ključni nalaz: enum garantuje da je ID validan, ali ne i tačan — ne
  bira ispravan među validnima.** Četvrti („Sony") model je pročitao kao brend, ne kategoriju.
- **3 su apstinirala na maglovitim jednorječnim upitima.** Tu eval ima rupu: **„Ventilatori" se
  pojavljuje dvaput sa različitim očekivanim ID-em (112 i 245)** — nedobitno po definiciji; „Dodaci"
  je pregeneričko. Apstinencija je razumno ponašanje, a eval traži tačan ID.

### Negativci: 6/8 čisto
Dva pada (`cat-manual-typo-mobitejli`, `cat-manual-typo-raunari`) su typo-auto-korekcija → rutiranje
(`category_overview`). `raunari` je baš onaj **svjesno PRIHVAĆEN known-limitation** iz `STATUS.md`;
`mobitejli` je ista klasa.

## Dvije posljedice

1. **Pitanje „eksplicitan leaf/parent u promptu" je zatvoreno.** Selekcija je riješena (8/8), pa taj
   signal ne bi pomakao nijedan od ovih 7 — ostatak je *preciznost-leaf* + *dvosmislenost*, što je
   Faza-2 teritorija (pravi RAG bira po query-ju, ne po tačnom ID-u) i known-limit.
2. **Enumov predviđeni dobitak (4 wrong-id) NIJE stigao.** Otvoreno je da li 220-člani enum uopšte
   nosi teret ili je leaf-priority sam odradio onih 8 — to bi rekao jeftin `base` vs `enum` run
   (23 poziva).

## Preporuka
Ne juriti ovih 7 promptom (mapiraju se na known-limits / Faza-2). Sljedeće: ili pun re-confirm 250
za pravi acceptance broj, ili prvo izolovati enum (da odlučimo zadržavamo li ga prije nego ga
zapečemo u 250).

> Caveat: ovo je kombinovan run (enum + temp zajedno), pa se doprinosi ne razdvajaju. Temp je na
> ovim strukturnim padovima ravan kako je i predviđeno.
