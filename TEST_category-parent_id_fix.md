# TEST: Category parent_id fix

Manualni DoD test za `feat(rag): parent_id expansion u hard filter pretrage`
(commit 93b7502+). Provjerava da li search po root cat-u (npr. "Računari")
vraća proizvode iz cijelog podstabla umjesto samo direktnih.

## Kako pokrenuti

```bash
# 1. Skripta mora biti na disku. Ako nije, checkout iz branch-a:
git checkout claude/analyze-category-hierarchy-dIVqm -- evals/visualize_parent_expansion.py

# 2. RUN #1 — rag.py BEZ fix-a (npr. main grana ili pre-merge stanje)
python evals/visualize_parent_expansion.py
# → HTML u ~/Downloads/parent-expansion-{TS}.html, FAIL banner

# 3. Apliciraj fix (merge / cherry-pick / git checkout 93b7502 -- app/rag.py)

# 4. RUN #2 — ista komanda, drugi rezultat
python evals/visualize_parent_expansion.py
# → novi HTML, PASS banner, drugačije brojke
```

Skripta sama detektuje rag.py stanje inspekcijom source-a (tri provjere:
`_load_cat_descendants` helper, `self._cat_descendants` polje, `not in
valid_cats` filter). Ako sve tri prođu → fix primijenjen → PASS. Ako bilo
koja padne → FAIL.

## Šta znače kolone u HTML-u

| Kolona | Šta znači |
|---|---|
| **Current** | Pool proizvoda koji rag.py search() **trenutno** vraća za taj cat. Brojka u ovoj koloni se mijenja između RUN #1 i RUN #2. Crveno = pre-fix (mala), zeleno = post-fix (velika). |
| **Alternative** | Hipotetička brojka u drugom modu. Prikazuje se kao mala anotacija "(was N)" ili "(with fix: N)" pored Current. |
| **Δ (delta)** | Apsolutna razlika između direct pool-a i subtree pool-a. **Iste je u oba runa** jer su to sirove brojke iz baze. Mijenja se samo predznak vizualno. |
| **Coverage %** | Koliko subtree pool-a Current pokriva. Pre-fix root cat može imati 0% (cat 107 PC komponente), 1% (cat 148 TV), 10% (cat 17 Računari). Post-fix uvijek 100% za sve root-ove. |
| **Verdict** | PASS / FAIL / NA. PASS = cat trenutno pokriva ≥30% subtree pool-a. FAIL = ispod 30% (fix bi pomogao). NA = leaf cat, nema djecu pa nema relevantno. |

## Brojke koje očekuješ — primjer "Računari" (cat 17)

**Pre-fix (RUN #1):**
- Current pool: **20 proizvoda**
- Banner: ✗ FAIL
- Coverage: 10.2%

**Post-fix (RUN #2):**
- Current pool: **197 proizvoda** (+177)
- Banner: ✓ PASS
- Coverage: 100%

### Kategorije uključene u "Računari" subtree nakon fix-a

| Cat | Naziv | Proizvoda |
|---|---|---|
| 17 | Računari (root, direktno) | 20 |
| 99 | Tablet | 57 |
| 289 | Dodaci za tablet | 50 |
| 324 | Dodaci za notebook | 43 |
| 310 | Sredstva za održavanje | 18 |
| 233 | Desktop PC | 7 |
| 234 | Računari All-In-One | 2 |
| 93 | Desktop Brand Name | 0 |
| 101 | Produženje garancije | 0 |
| 322 | REFURBISHED DESKTOP | 0 |
| 323 | Server | 0 |
| 325 | Rezervni dijelovi informatika | 0 |
| **Σ** | **subtree pool** | **197** |

Napomena: cat 93 (Desktop Brand Name), 322, 323, 325 i 101 trenutno imaju 0
proizvoda u bazi, ali su strukturalno u podstablu i biće automatski uključeni
ako se naseliti.

## Brojke za ostale root kategorije

| Root cat | Naziv | Pre-fix | Post-fix | Δ | Notable djeca |
|---|---|---:|---:|---:|---|
| 151 | Mobiteli | **5** | **1575** | +1570 | 394 Maske (1274), 175 Mobilni telefoni (167), 176 Dodaci (129) |
| 219 | PC periferija | **0** | **638** | +638 | 221 Slušalice (284), 220 Tastature (99), 279 Zvučnici (82), 307 Podloge za miševe (62) |
| 356 | Kablovi i adapteri | **0** | **280** | +280 | 137 USB kablovi (123), 316 Video kablovi (83), 287 Audio (20) |
| 107 | PC komponente | **0** | **255** | +255 | 118 Kućišta (58), 111 CPU coolers (33), 115 SSD (30), 113 RAM (18), 108 Matične ploče (16) |
| 352 | Mrežna oprema | **0** | **203** | +203 | 298 Mrežni alat (88), 309 Router-i (46), 270 Switch-evi (43) |
| 17 | **Računari** | **20** | **197** | +177 | 99 Tablet (57), 289 Dodaci za tablet (50), 324 Dodaci za notebook (43) |
| 148 | TV i prateća oprema | **1** | **170** | +169 | 165 Nosaci za TV (76), 163 Televizori (68), 166 Ostala oprema (24) |
| 97 | Printeri i skeneri | **1** | **16** | +15 | 127 Multifunkcijski (10), 124 Laserski (5) |

## Šta vidiš u HTML-u

**Verdict banner gore:**
- Pre-fix: crveni "✗ FAIL — rag.py parent expansion fix NIJE primijenjen",
  evidence lista pokazuje sve tri provjere kao NO.
- Post-fix: zeleni "✓ PASS — rag.py parent expansion fix JE primijenjen",
  evidence lista pokazuje sve tri provjere kao YES.

**Summary stat-ovi:**
- Σ root pool: u pre-fix runu se zove "bez fix-a (current)" i pokazuje malu
  brojku (svih root cat-ova ukupno ~30 proizvoda). U post-fix runu se zove
  "sa fix-om (current)" i pokazuje veliku brojku (~4700+ ukupno).
- Parents FAIL: pre-fix oko 28 root cat-ova ispod threshold-a, post-fix 0.

**Top 15 leaderboard:**
- Pre-fix: "Current" kolona crveno (male brojke), "Alternative" zeleno (velike).
- Post-fix: kolone zamijene boju — "Current" zeleno (velike), "Alternative"
  crveno (male).

**Full tree:**
- Pre-fix: root cat-ovi imaju FAIL badge i mali broj pored imena
  (npr. "Računari 20").
- Post-fix: isti root-ovi imaju PASS badge i veliki broj
  (npr. "Računari 197 (was 20)").

## DoD kriterijum

Test se smatra **prošlim** ako:
1. RUN #1 (bez fix-a) generiše HTML sa crvenim FAIL banner-om i `exit code 1`
2. RUN #2 (sa fix-om) generiše HTML sa zelenim PASS banner-om i `exit code 0`
3. Brojke u "Current" koloni se mijenjaju između runova — npr. cat 17 ide
   sa 20 na 197, cat 107 sa 0 na 255, cat 151 sa 5 na 1575.

Ako RUN #2 i dalje pokazuje FAIL, ili brojke su iste, fix nije pravilno
primijenjen — provjeri `app/rag.py` da li sadrži `_load_cat_descendants`,
`self._cat_descendants` i `not in valid_cats` u search() filteru.
