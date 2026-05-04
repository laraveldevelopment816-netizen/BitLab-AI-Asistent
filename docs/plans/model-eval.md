# Resolucija: Sedmica testiranja modela (Sesija 9)

> **Cilj:** Do **2026-05-11** (kraj sedmice) doneti **ekonomsku odluku** o
> chat modelu zasnovanu na **podacima**, ne na intuiciji ili default-u.
> **Tehnički prag:** ≥99% pass rate na proširenom eval setu.
> **Ekonomski prag:** najjeftiniji model koji prelazi tehnički prag.
> **Status:** otvoreno (Sesija 9).

---

## 1. Pozadina

Sesija 8 je hotfix-om prebacila chat sa Haiku 4.5 na Sonnet 4.6 zbog dva
production bug-a (typo handling + halucinacije zaliha — vidi
`tests/test_typo_robustness.py`). Ovo je pragmatično, ne optimalno.

**Subjektivna hipoteza Ivana** (zahtjeva validaciju podacima — *NE prihvataj
kao činjenicu prije eval-a*):

> "Mislim da će nam ovdje neki GPT mini završiti priču sa istom ili sličnom
> potrošnjom kao Haiku. Ima dosta opcija — GPT-evi su dobri i baš jeftini
> za ovu namjenu, čak i Llama varijante isto dobro rade klasifikaciju.
> Ali to treba testirati tokom sedmice, pa onda uporediti rezultate i
> odlučiti šta je najbolje."

Ovo je hipoteza, ne preporuka. Eval mora da je podrži ili obori.

---

## 2. Kandidati za eval

| Provider | Model | Input $/1M | Output $/1M | Hipoteza |
|---|---|---|---|---|
| Anthropic | Claude Sonnet 4.6 | 3.00 | 15.00 | **Trenutni baseline** (100% eval, $2.40/mj) |
| Anthropic | Claude Haiku 4.5 | 1.00 | 5.00 | Pao 94.4%, halucinacije — kontrola, vjerovatno odbačen |
| Anthropic | Claude Opus 4.7 | 15.00 | 75.00 | Kontrola "best possible" (treba da prešiša Sonnet) |
| OpenAI | GPT-4o-mini | 0.15 | 0.60 | **Glavni Ivan-ov favorit** — 20× jeftiniji od Sonneta |
| OpenAI | GPT-4.1-mini (ako live) | 0.40 | 1.60 | Sredina, najnoviji |
| OpenAI | GPT-4o | 2.50 | 10.00 | Kontrola — sličan price-point kao Sonnet |
| Meta (Groq) | Llama 3.3 70B | 0.59 | 0.79 | Inference brz na Groq-u, jeftin |
| Meta (Groq) | Llama 3.1 8B | 0.05 | 0.08 | Najjeftiniji kandidat — ako prođe, win |
| DeepSeek | DeepSeek-V3 | 0.27 | 1.10 | Ozbiljno potcijenjen ovih dana, vrijedi probati |

> **Napomena:** cijene su približne na dan 2026-05-04 i treba ih provjeriti
> kod svakog provider-a prije final analize.

---

## 3. Metodologija

### 3.1 Tehnički eval (objektivno, automatski)

`evals/run_categories.py` se proširuje na sve kandidate:

1. **Klasifikacioni accuracy** — trenutni eval set proširen na **60-80
   upita** (od trenutnih 41), uključujući:
   - 36 baseline cases
   - 5 typo cases (Sesija 8 hotfix)
   - +20 novih: kombo proizvodi ("tastatura i mis"), apstraktni upiti
     ("nešto za firmu"), B2B intent, multi-turn kontekst
2. **Tool-calling robustnost**:
   - Procenat upita gdje agent pozove `search_products` u prvoj iteraciji
   - Procenat halucinacija nakon non-empty tool result-a (target: 0%)
3. **Latency** (median, p95)
4. **Cost per request** (mjereno, ne procenjeno)

**Prag:** model je kandidat za prod ako **klasifikacioni accuracy ≥99%** i
**halucinacije = 0%** na cijelom setu.

### 3.2 Subjektivni eval (kvalitativno, ručno)

Tim (Ivan + ko god demonstrira) prolazi kroz **15 realnih scenarija** iz
production loga (Live tab dashboarda) i ocijenjuje **5-pt Likert** po
kategorijama:
- Razumljivost odgovora
- Stil (prijateljski profesionalan)
- Korektnost (faktičko)
- Tempo (brzina + dužina)
- Spremnost za eskalaciju (kad treba)

**Prag:** prosjek ≥4.0 po kategoriji.

### 3.3 Ekonomska odluka

Posle tehničkog + subjektivnog evala:

```
kandidat = svi modeli koji su prošli tehnički prag (≥99%)
filter   = oni koji su prošli subjektivni prag (≥4.0/5.0)
odabir   = najjeftiniji u filteru × očekivani volumen
```

Ako **niko ne prelazi 99%**, vraćamo se na Sonnet 4.6 i revidiramo prompt
za sljedeću iteraciju.

---

## 4. Implementacija (šta treba da uradimo ove sedmice)

### Sesija 9.1 — Multi-provider abstraction (Sonnet 4.6 medium, ~90m)

`app/models.py` — adapter sloj koji omogućava da `run_agent()` zove bilo
koji provider sa istim interfejsom. Pristup:

- **Anthropic-native:** preko `anthropic` SDK
- **OpenAI:** preko `openai` SDK (Chat Completions sa tool use; treba
  konvertor za tool schema format jer su slično ali ne identično)
- **Groq:** OpenAI-compatible endpoint (Llama)
- **DeepSeek:** OpenAI-compatible endpoint

Svaki adapter izlaže:
```python
def run(messages, system, tools) -> AgentResult
```

Tool schema konverzija je glavna komplikacija — Anthropic format
(`{name, description, input_schema}`) vs OpenAI (`{type: "function",
function: {name, description, parameters}}`). Adapter sloj radi tu
transformaciju.

### Sesija 9.2 — Eval set proširenje (Opus high, ~45m)

20 novih realnih upita (iz production loga + scenariji koje Ivan opiše).

### Sesija 9.3 — Multi-model eval runner (Sonnet medium, ~60m)

`evals/run_models.py` pokreće cijeli set kroz svaki kandidat, generiše
markdown tabelu sa accuracy / latency / cost po modelu:

```
Model              | Accuracy | Hallucinations | p50 lat | p95 lat | $/1k
-------------------|----------|----------------|---------|---------|-----
Sonnet 4.6         |  100.0%  |  0.0%          |  4.2s   |  8.1s   | 2.40
GPT-4o-mini        |   ?      |   ?            |   ?     |   ?     | 0.12
Llama 3.3 70B      |   ?      |   ?            |   ?     |   ?     | 0.20
...
```

Output ide u `evals/results/2026-05-XX-comparison.md` (date-stamped).

### Sesija 9.4 — Compare panel proširenje (Sonnet medium, ~30m)

Trenutni dashboard Compare panel zna samo za "haiku" i "sonnet"
(Anthropic). Proširiti na cijelu listu kandidata. Backend
`POST /api/dashboard/compare` već podržava listu modela — treba
proširiti `model_registry` u `config.py` kad multi-provider adapter
postoji.

### Sesija 9.5 — Subjektivna ocjena (Ivan, manuelno, ~60m)

Ivan otvara Compare panel sa 15 scenarija, popunjava 5-pt Likert tabelu
za svaki kandidat. Output: `evals/results/2026-05-XX-subjective.md`.

### Sesija 9.6 — Final odluka + migracija (Sonnet low, ~30m)

Markdown writeup sa odlukom + razlogom. Ako se mijenja default model,
update `app/config.py` + dokumentacija + regression run.

---

## 5. Schedule (target)

| Datum | Aktivnost | Vlasnik |
|---|---|---|
| 2026-05-05 | Sesija 9.1 — Multi-provider abstraction | Claude |
| 2026-05-06 | Sesija 9.2 — Eval set proširenje | Claude + Ivan |
| 2026-05-07 | Sesija 9.3 — Multi-model eval runner + prvi run | Claude |
| 2026-05-08 | Sesija 9.4 — Compare panel proširenje | Claude |
| 2026-05-09 | Sesija 9.5 — Ivanova subjektivna ocjena | Ivan |
| 2026-05-10 | Buffer dan (ako neki provider zahtjeva auth ili rate limit problem) | — |
| 2026-05-11 | Sesija 9.6 — Final odluka + commit | Claude + Ivan |

---

## 6. Decision criteria — eksplicitno

Odluka kraj sedmice sledi ove pravce (po prioritetu):

1. **Tehnička pouzdanost je preduslov.** Bez ≥99% accuracy + 0%
   halucinacija, model nije kandidat. Ne možemo nuditi proizvode koje
   nemamo na zalihi (legal risk + reputacija).
2. **Subjektivni utisak je preduslov.** Bez ≥4.0/5.0 prosjeka po
   kategoriji, model nije kandidat. Korisnici primjećuju "robotski"
   stil ili previše dugačke odgovore — utiče na conversion.
3. **Ekonomski parametar bira između preživjelih.** Najjeftiniji model
   po projekciji za 12 mjeseci × očekivani volumen.
4. **Lock-in tjebreaker:** ako su dva kandidata blizu (cijena u 20%
   razlike), ide onaj sa boljim provider track record-om (uptime,
   stabilnost API-ja, predvidiva cijena).

---

## 7. Šta NIJE u skopu ove sedmice

- Fine-tuning custom modela (Llama LoRA, OpenAI fine-tune) — to je
  zaseban projekat sa drugačijim ROI-jem
- Embedding model promjena (i dalje koristimo MiniLM-L12-v2 lokalno)
- TTS/STT model promjena (Azure + Groq Whisper rade kako rade)
- Promjena agent loop strukture — samo zamjena LLM-a iza istog interfejs-a

---

## 8. Open questions (Ivan, podsjeti me da pitam)

- Da li prihvatamo dodatne env vars na produkciji (`OPENAI_API_KEY`,
  `GROQ_API_KEY`, `DEEPSEEK_API_KEY`) ili samo testiramo lokalno pa
  prebacujemo izabrani na server?
- Volumen: koliko upita/mjesec realistično očekujemo poslije pune
  produkcije? Ovo bitno za ekonomsku projekciju.
- Da li je B2B kanal (email auto-reply) takođe u opsegu testiranja, ili
  ostaje na Sonnet 4.6 nezavisno od chat odluke? Email zahtijeva drugačiji
  stil i ne bismo htjeli da Llama 8B piše formalne ponude.

---

## 9. Subjektivna hipoteza vs realnost

Ovaj dokument **eksplicitno odvaja** Ivanovu subjektivnu hipotezu od stvarnog
tehničkog rezultata:

| Faza | Status |
|---|---|
| **Hipoteza** (sekcija 1) | "GPT mini će biti dovoljan i jeftiniji od Haiku-a" |
| **Tehnički test** (Sesija 9.3) | TBD — eval pass rate + halucinacije |
| **Subjektivni test** (Sesija 9.5) | TBD — Likert ocjena |
| **Realnost** (Sesija 9.6) | TBD — final pisani writeup |

Kraj sedmice posebno upoređujemo hipotezu sa realnošću — ako se podudaraju,
odličan poziv. Ako ne, dokumentujemo zašto da bismo naučili nešto za
sljedeću tehničku odluku.
