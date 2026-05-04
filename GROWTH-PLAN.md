# Resolucija: Growth — SEO, link building, automatizacija (Sesija 10+)

> **Cilj:** Povećati organski reach i prodaju **webshop.bitlab.rs** korišćenjem
> Claude Max plana za inteligentnu automatizaciju + dubinski research, umjesto
> manuelnog SEO/marketing rada koji je danas norma u regiji.
> **Status:** otvoreno (Sesija 10), pokreće se paralelno sa Sesijom 9 (model eval).
> **Period:** kontinuirano — prva faza 4 sedmice, pa monthly cadence.

---

## 1. Polazna pretpostavka

Lokalni IT webshopovi u BiH/RS (Comtrade Shop, ADM Solutions, Kim Tec, Nest,
WinWin) plaćaju agencije za SEO + Google Ads + content production. Naš
**komparativni argument**: imamo Claude Max plan koji za isti novac može da
producira kvalitetan content, radi competitive research, drafta backlink
outreach, optimizuje produkt opise — **uz human-in-the-loop verifikaciju**.

**Ne ignorišemo profesionalce** — koristimo ih gdje su nezamjenljivi (legal,
PR, lokalni partneri). AI radi obim koji bi inače bio prohibitivan.

---

## 2. Šta tačno hoćemo

| Metrika | 90 dana | 180 dana | Mjerenje |
|---|---|---|---|
| Organic sessions / mjesec | +50% | +150% | GA4 (acquisition → organic search) |
| Indexovane stranice | +30% | +80% | Google Search Console (coverage) |
| Backlinkovi (referring domains) | +20 | +60 | ahrefs free trial / Ubersuggest |
| Conversion rate iz organike | +0.3pp | +1pp | GA4 conversion event setup |
| Average position za top 50 keyword-a | top 10 → top 5 | top 5 → top 3 | GSC performance |
| Branded vs non-branded traffic | 80/20 → 60/40 | 60/40 → 50/50 | GSC search type filter |
| AI chat conversion (već imamo) | baseline | +20% | naš dashboard `/api/dashboard/stats` |

Sve metrike imaju target koji je **provjerljiv i dokumentabilan**. Ne pratimo
"brand awareness" niti slične mekane KPI-ove na koje se SEO agencije love.

---

## 3. Faze plana

### Faza 0 — Setup analytics i baseline (sedmica 1, ~6h)

**Cilj:** ne možemo ništa optimizovati prije nego što imamo brojke.

- GA4 setup ako nije (provjeri webshop)
- Google Search Console verifikacija
- Sitemap submit (`sitemap.xml`, provjeri da li ga generiše webshop platforma)
- Bing Webmaster Tools (10% market u regiji nije za zanemariti)
- Ahrefs/Ubersuggest free trial za baseline backlink snimak
- Lighthouse audit svih top 20 stranica
- **Output:** `growth/baseline-2026-05-XX.md` sa svim brojkama

### Faza 1 — Dubinski tehnički audit (sedmica 1-2, ~12h)

Claude radi audit, dokumentuje, predlaže fix listu sa prioritetom (P0
blocker, P1 important, P2 nice-to-have). **Ne fixira ništa bez Ivanovog OK**.

Šta auditujemo:
- **Core Web Vitals** (LCP, FID, CLS) — Lighthouse + PageSpeed Insights
- **Crawlability**: robots.txt, sitemap, canonical tags, hreflang ako bude
  potrebno (BiH/RS dijalekti)
- **Schema.org markup**: Product, BreadcrumbList, Organization, FAQPage,
  Review (kritično za rich snippets)
- **Internal linking**: orphaned pages, link depth, anchor text distribution
- **Duplicate content**: kategorijske + filterske stranice
- **Mobile usability**: responsive issues, tap target sizes
- **HTTPS / SSL**: cert chain, mixed content
- **Page speed budget**: imamo li 3rd party scriptova koji sjede 500ms+?
- **Pagination**: rel=next/prev ili infinite scroll SEO-friendly?
- **404 handling**: soft 404 vs proper, redirect mapping
- **AI widget impact na SEO**: provjeri da widget.js ne blokira render,
  da nema CLS shift, da nije u initial bundle

Output: `growth/audit-2026-05-XX/{technical.md, content.md, structured-data.md}`
+ priority sheet (Linear/Notion ili samo markdown checklist).

### Faza 2 — Kompetitivni audit (sedmica 2, ~8h)

5-7 konkurenata u regiji + 3 globalna IT shopa kao reference.

Po konkurentu:
- Top 100 organic keyword-a (preko ahrefs trial-a)
- Backlink profile (nove referring domains zadnja 3 mjeseca)
- Content cadence (koliko često objavljuju, koje kategorije)
- Page structure top kategorija (h1, intro, faq, tabela, CTA)
- Tech stack indicators (Magento? OpenCart? Custom?)
- Schema markup šta koriste

Output: `growth/competitors-2026-05-XX.md` sa **content gap analizom** —
keyword-i gdje imaju traffic a mi ne, gdje smo iza za 5+ pozicija a možemo
napasti, koje stranice tipa nemaju (Comtrade nema "kako odabrati SSD"
vodič — to je naša prilika).

### Faza 3 — Keyword strategy + content plan (sedmica 2-3, ~10h)

Ne bavimo se "SEO content" u smislu fluff-a. Pravimo content koji rješava
realne korisničke probleme i istovremeno ulazi u rezultate pretrage.

Tri tipa stranica u prioritetu:

1. **Product page optimizacija** (postojeće, najveći ROI):
   - Koristi naš AI asistent da iz `data/products.meta.json` + opisa
     producira **strukturisan opis** sa H2 sekcijama: "Koji [proizvod]
     odabrati", "Specifikacije", "Za koga je", "Alternativa"
   - FAQ sekcija po proizvodu (Schema.org FAQPage markup → rich snippets)
   - Šta nije: copywriting iz vakuuma. Claude koristi stvarne specs +
     cijenu + dostupnost iz našeg indeksa

2. **Kategorijske vodiče** (novo, srednji ROI):
   - "Najbolji SSD do 200 KM 2026" — vodič tipa, sa stvarnim našim
     proizvodima, ne generic
   - "ASUS vs Lenovo laptopi za studente" — comparison tipa
   - 1 vodič / sedmica = 12 vodiča / kvartal, target po vodiču: top 10 za
     primarnu frazu u 90 dana

3. **FAQ & how-to** (P3, dugoročno):
   - "Kako instalirati SSD u laptop" — bridge content, niska konkurencija
     u BCS-u, dovodi traffic koji konvertuje na proizvod

Claude Max je tu glavni resource — drafta sve, čovjek edituje 20%, objavljuje.

Output: `growth/content-plan-2026-Q2.md` sa kalendarom, primarnim
keyword-om po stavci, target URL-om, internim linkovima.

### Faza 4 — Link building automatizacija (sedmica 3-4, ~10h, kontinuirano)

**Ne kupujemo linkove** (Google ban risk + nije fer prema tržištu). Radimo:

1. **Lokalni katalozi** (BiH/RS biz directorije, IT-specifični):
   - lista 50+ relevantnih, automatski popunjavamo (Claude generiše
     submission tekst, čovjek klika kroz)
2. **Partnerski outreach**:
   - lokalni IT bloger-i, YouTuber-i (review programs sa našim
     proizvodima na pozajmicu)
   - lokalne web agencije (resell partnerstva)
   - univerziteti / fakulteti (popusti za studente → backlink iz
     student union sajta)
3. **HARO/Helpacrowdsourceofknowledge alternative** za BCS market:
   - klikx.com / b92.net tech rubrike — pitch-uju expert komentar na
     tech teme; Claude drafta odgovore, čovjek šalje
4. **Digital PR**:
   - kvartalna content piece tipa "Stanje IT tržišta u BiH 2026" sa
     stvarnim podacima iz našeg kataloga (cjenovni trendovi, najprodavanije
     kategorije) — pitch-uje se medijima, daje se besplatno za reuse uz
     atribuciju

Output: `growth/link-building-2026/` folder sa kontaktima, statusom,
template-ima.

### Faza 5 — Paid ads automatizacija (sedmica 4+, kontinuirano)

Kombinujemo Google Ads + Meta Ads sa **product feed automatizacijom**.

- **Google Shopping**: feed iz `data/all-products.json` → Merchant Center
  → Performance Max kampanja. Automatski refresh dnevno (već imamo cron
  predviđen za index refresh).
- **Meta Ads**: catalog ads (isti feed), retargeting iz GA4 audiences
- **Smart creative rotation**: Claude generiše 5 varijanti ad copy-ja
  po proizvodu, mjerimo CTR, automatski pause-uje loše varijante
- **Budget cap**: agresivno ograničen u prvom mjesecu (€100-200/mj)
  dok ne imamo pouzdane CAC/LTV brojke

Output: `growth/paid-ads-playbook.md` sa kampanjama, budgetima, A/B
matricom.

### Faza 6 — AI asistent kao growth tool (kontinuirano)

Ovo je naš **unfair advantage** — niko drugi u regiji nema chat AI
asistenta na webshopu. Iskoristimo ga:

1. **Email capture**: kad korisnik ostavi pitanje van radnog vremena,
   asistent traži email "da se prodajni tim javi" → newsletter pool
2. **Newsletter content**: mjesečni "šta je novo u IT-u" generiše
   Claude iz našeg kataloga + nedavnih vijesti. Šaljemo iz n8n
   workflow-a
3. **Cart abandonment recovery**: ako korisnik napusti razgovor sa
   "interesovan sam za laptop", asistent zna kontekst → email follow-up
   sa konkretnim preporukama
4. **Review request automation**: nakon dostave (n8n trigger iz
   webshop-a), Claude generiše personalizovan zahtjev za review
   po jeziku/stilu kupca
5. **Insights iz log-a**: Sesija 8 dashboard već sadrži sve chat-ove.
   Mjesečno extraction-uju se nepokriveni upiti → backlog za content
   plan ("korisnici često pitaju X, mi nemamo content za to")

---

## 4. Šta NIJE u skopu

- **Black-hat SEO**: PBN-ovi, kupljeni linkovi, doorway pages — ban risk
- **Spamerski email**: nikakav cold outreach bez opt-in
- **Lažni reviews**: čekamo prirodne, ne fabrikujemo
- **Translation farming**: ne pravimo verzije sajta na 10 jezika za
  Google traffic — fokus je BiH/RS market
- **AI-generated thin content**: 1.000 stranica "kako kupiti X" gdje su
  sve iste — ban risk, plus kvari brand
- **Affiliate marketing as primary**: ne stavljamo reklame tuđih
  proizvoda na naš sajt; mi smo prodavac, ne marketingaš

---

## 5. Mjerenje uspjeha (kvartalni review)

Svaki kvartal Ivan + ja pravimo writeup sa:

- Brojke iz Sekcije 2 (planirano vs stvarno)
- Top 5 stvari koje su radile (skaliramo)
- Top 5 stvari koje nisu radile (mijenjamo ili odbacujemo)
- Šta je AI uradio sam vs šta je trebalo human review (kalibracija)
- Cost-benefit: koliko Claude API + alata smo potrošili vs revenue
  attribution iz organic + paid

Output: `growth/review-2026-Q2.md`, `growth/review-2026-Q3.md` itd.

---

## 6. Veza sa ostalim sesijama

- **Sesija 9 (model eval)**: ako prebacimo chat na jeftiniji model,
  troškovni budget za ovaj plan se povećava (manje na inference, više
  na content generaciju + ads)
- **Sesija 8 dashboard**: Live tab + Stats nam daju realnu sliku
  korisničkog ponašanja → input za content plan
- **n8n workflow**: link building outreach + newsletter + cart
  abandonment idu kroz n8n (već imamo infrastrukturu)
- **Buduća Sesija 11**: A/B testing framework za product page varijante
  (ovo dolazi tek kad imamo 1.000+ posjeta/dan po stranici)

---

## 7. Open questions

- Ko ima pristup webshop CMS-u za schema markup + meta tag izmjene?
  (Treba developer hour budget ili admin pristup za nas)
- Postojeći SEO agencija — ako postoji, šta su trenutno radili,
  preklapamo li se?
- GA4 history — ako postoji 12+ mjeseci podataka, imamo seasonal
  baseline; ako ne, prvih 90 dana je learning period
- Budgetna granica za paid ads (€/mj) — bez ovoga ne možemo planirati
  Fazu 5
- Pravna provjera za digital PR pieces (cijene konkurencije u
  "Stanje tržišta" reportima može biti osetljivo)

---

## 8. Subjektivna procjena (čekamo realnost)

Moja pretpostavka — pošto je AI asistent već na sajtu i radi, glavni
ROI ovog plana je u **content + organic SEO** (Faze 1-3), ne u paid
ads. Konkurencija u BCS region je slabija na content kvalitetu nego na
budgetu, što je naša prednost. Paid ads je ozbiljan tek kad organic
pipeline radi.

**Ovo je hipoteza, ne preporuka.** Faza 0 baseline + Faza 2 competitive
audit će pokazati gdje je realan ROI. Kvartalni review revidira
strategiju ako se pokaže drugačije.

---

## 9. Schedule (target za prve 4 sedmice)

| Sedmica | Faza | Output |
|---|---|---|
| 2026-W19 (12-18.05) | F0 + F1 baseline | analytics setup, tehnički audit |
| 2026-W20 (19-25.05) | F1 fixes + F2 | tehnički fixovi P0, kompetitivni audit |
| 2026-W21 (26.05-01.06) | F3 | content plan Q2, prvi vodič objavljen |
| 2026-W22 (02-08.06) | F4 + F5 | link building outreach pokrenut, paid ads pilot |
| 2026-W23+ | F6 + monitoring | AI asistent kao growth tool, mjesečni review |

Ne hard-codujemo dalje — kvartalni review (kraj juna) revidira plan.
