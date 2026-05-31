# Eval regresija — iter17 (prompt fix Group A+B)

> Analiza 2026-05-29, grana `feat/ralph-categories-eval`. Poređenje dva **puna**
> (250) eval kruga iz `evals/runs/*.jsonl` koji su trenutno u repou. Dio
> istorije je obrisan, pa je baseline ono što je dostupno — iter8.

## Ukratko

Prompt fix (Group A + B, commiti `816e46e` i `f9c4d9a`) je **pogoršao** eval, ne
popravio. Na istih 212 entry-ja koji su u oba kruga: baseline (iter8) **84.4%**,
drugi krug poslije fix-a (iter17-final) **79.2%**. Fix je popravio 18 slučajeva,
ali pokvario 29 — neto **−11**.

Najvažnije i iznenađujuće: **svih 29 regresija je isti kvar — model NIJE pozvao
nijedan tool.** Nula slučajeva "pozvao pogrešan tool". Na čistim, jednoznačnim
leaf upitima ("Matične ploče", "Mobilni telefoni", "Kopir aparati") koje je
baseline rješavao jednim tačnim `search_products(leaf_id)` pozivom, drugi krug
vraća izmišljenu listu proizvoda sa cijenama i URL-ovima — bez ijednog tool
poziva. Dakle halucinacija.

Ironično je da je upravo **Group B** trebao da UBIJE halucinaciju i natjera tool
poziv. Neto efekat je obrnut: apstinencija od toola je **porasla** (24 → 37
"NONE" na 212), a model na tim slučajevima izmišlja katalog. Pa zaključak nije
"jedno pravilo je pogrešno" — nego je prompt **pretrpan**, i nova imperativna
pravila (A+B) su pokvarila lak, ranije-prolazan put.

Loop **nije** prošao acceptance (cilj ≥95%, sad 79.2% i ispod baseline ~85%) —
dakle bitlab nije korak do gotovog na ovom putu.

## Detaljnije

**Šta je upoređeno.** Dva puna kruga (oba `mode=full`, cijeli set — ne sample):
- baseline: `categories-ralph-iter8-pattern-analysis.jsonl`
- poslije fix-a: `categories-ralph-iter17-prompt-fix-final.jsonl`
  (pauziran budget gate-om na 212/250 — checkpoint `next_index=212`)

Bitno: i prvi krug je bio pun 250 (~85%). Ovo **nije** priča "validirano samo na
malom sample-u". Mali sample-ovi (10/10, 7/7, 30/30) su bili samo **međukorak**
validacije prompta prije punog re-runa — i baš su dali lažni zeleni signal:
93–100% na sample-u dok je pun set pao na 79%.

**Brojevi (zajednički 212 entry-ja):**

| metrika | baseline (iter8) | 2. krug (iter17-final) |
|---|---|---|
| PASS rate | 84.4% (179/212) | 79.2% (168/212) |
| PASS→FAIL (pokvareno) | — | 29 |
| FAIL→PASS (popravljeno) | — | 18 |
| neto | — | −11 |

**Gdje i kako je puklo:**
- 26/29 regresija u `cat-leaf`, 3 u `cat-parent`.
- **29/29 regresija: nijedan tool poziv** (`actual_tool_calls` prazan). Kvar je
  APSTINENCIJA, ne pogrešno rutiranje.
- Apstinencija porasla i šire: NONE tool-poziva 24 (baseline) → 37 (2. krug).
- Reply na tim slučajevima = izmišljen katalog. Konkretno:
  - `cat-leaf-101` "Produženje garancije": baseline `search_products(101)` PASS
    → 2.krug NONE, izmislio APC garantne pakete sa cijenama (94,69 / 152,76 KM…).
  - `cat-leaf-108` "Matične ploče": baseline `search_products(108)` PASS →
    2.krug NONE, izmislio tabelu od 22 ploče (ASUS…).
  - `cat-leaf-128` "Kopir aparati": baseline `search_products(128)` PASS →
    2.krug NONE, izmislio 5 Ricoh modela + `bitlab.ba` URL-ove.
  - `cat-leaf-167` "Rezervni dijelovi elektronika", `-175` "Mobilni telefoni",
    `-176` "Dodaci za mobitele", `-168` "Projektori" — isti obrazac.

**Šta je fix tačno dodao** (`app/agent.py:SYSTEM_PROMPT_V1`):
- Group A (`816e46e`): "LEAF PRIORITET" — ako se ime pojavljuje egzaktno ILI kao
  **podstring** u leaf listi, OBAVEZNO biraj leaf; + "tačan ID match".
  ~18 linija sa nabrojanim primjerima.
- Group B (`f9c4d9a`): "ZABRANA HALUCINACIJE" + "OBAVEZNO PROBAJ TOOL".
  ~18 linija.
- Neto: prompt narastao za ~36 linija gustih imperativa ("OBAVEZNO", "STROGO
  ZABRANJENO", "kritično"), naslaganih preko postojećeg pravila "ako je
  dvosmislen NE zovi tool".

## Zašto (kratko — detalj ostaje za idući korak)

Radna hipoteza: **prompt overload / sukob imperativa.** Što je više pravila
naslagano ("budi oprezan / razlikuj leaf-parent / ne izmišljaj / zovi tool samo
kad…"), to je model na jednostavnoj većini slučajeva postao manje pouzdan —
preskače tool i puni odgovor iz memorije. Poznat failure mode: over-instruction
obara instruction-following na lakim slučajevima dok juriš teške. Koje pravilo
tačno najviše doprinosi (dužina vs konkretan konflikt) — to je sljedeći korak.

## Way forward (za zajedničku diskusiju)

1. **Vrati iter8 prompt kao baseline** (84.4%) — trenutno najbolji koji imamo.
   A+B ga obaraju, ne smiju ostati kao default.
2. **Izmjene jedna-po-jedna, pun eval kao gate** — ne sample. Sample je lagao
   (93–100% dok je pun set 79%). Ako je pun set preskup, gejtuj na stratifikovani
   sample koji UKLJUČUJE baš leaf slučajeve koji su pukli.
3. **Hipoteza "manje je više":** probaj da prompt **skratiš**, ne produžiš.
   Možda iter8 + samo Group B anti-halucinacija (bez Group A dužine) digne
   rezultat. Mjeri svaku izmjenu posebno.
4. **Ručna error-analiza** na 29 NONE-regresija (`cat-leaf-101,108,128,167,168,
   175,176,200,205,207,210,222,224,239…`) + na originalne baseline FAIL-ove —
   ljudski posao, ne još jedan autonomni loop.
5. **Veliko pitanje: nastaviti li autonomni Ralph za OVO?** Loop je 36h/22 iter
   "radio" i otišao unazad jer gejtuje na lošem signalu i sam committa prompt
   izmjene. Za suptilni prompt trade-off čovjek-u-petlji (gledaš 5–10 fail
   primjera → mijenjaš jedno pravilo → mjeriš pun set) je vjerovatno brži i
   sigurniji. Ralph je bolji za mehanički rad (refactor, dodavanje testova).

Acceptance je ≥95% (`STATUS.md`). Realno: prvo vrati na ~85%, pa pažljivo gore.
Otvoreno: je li 95% pravi ship-bar, ili se može shipovati na ~85% sa "nisam
siguran, evo opcija" fallback-om za nisko-confidence slučajeve.
