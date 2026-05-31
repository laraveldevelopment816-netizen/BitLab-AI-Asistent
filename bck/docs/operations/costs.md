# Troškovi

## Procjena za ~1.000 chat upita / mjesec

| Servis | Plan | Cijena per 1M tokena | Procena |
|---|---|---|---|
| Claude Sonnet 4.6 (chat + voice + email) | Pay-as-you-go | $3 in / $15 out | ~$2.40 |
| Claude Haiku 4.5 (samo Compare drugi pol za A/B testing) | Pay-as-you-go | $1 in / $5 out | ~$0.20 |
| Azure Speech Services (TTS + STT) | Free tier | $0 | 500K znakova/mj TTS + 5h STT |
| Groq Whisper (STT fallback) | Free tier | $0 | 7.200s/dan |
| sentence-transformers + faster-whisper | Lokalno | $0 | $0 uvijek |
| n8n (lokalni Docker) | Self-hosted | $0 | bez limita |
| VPS (Ubuntu, 2 vCPU / 2 GB RAM) | Hetzner CX22 ili sl. | ~€4/mj | fixna |
| **Ukupno** | | | **~€6–9/mj** |

## Stvarni troškovi po requestu

Vidljivi u **Stats** tab dashboarda:
- Total cost (cumulative od početka logging-a)
- Per-adapter breakdown (chat:haiku vs chat:sonnet vs voice:sonnet vs email:sonnet)
- Per-request u RequestDetail

## Cost izračun

`app/server/dashboard.py` `COST_PER_M`:

```python
COST_PER_M = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
}
```

Per request:
```python
cost_usd = (tokens_in × in_rate + tokens_out × out_rate) / 1_000_000
```

Primjer realnog upita "imate li tastaturu" (Stats tab snimljeno):
- **Haiku:** 9.467 in / 215 out → $0.0105 (1 cent)
- **Sonnet:** 13.834 in / 257 out → $0.0454 (4.5 centi)

Sonnet ~4.3× skuplji per upit, ali sa boljim formatiranjem i typo handling-om (zbog čega je default poslije Sesija 8 hotfix).

## Volume sensitivity

| Volume / mj | Sonnet trošak | Haiku trošak (ako prebacimo) |
|---|---|---|
| 1.000 | ~$3 | ~$1 |
| 10.000 | ~$30 | ~$10 |
| 100.000 | ~$300 | ~$100 |

Sa rastom volumena, razlika postaje materijalna. Sesija 9 ([`../plans/model-eval.md`](../plans/model-eval.md)) testira jeftinije modele (GPT-4o-mini, Llama 3.x, DeepSeek-V3) sa target-om ≥99% accuracy + 0% halucinacija — ako prođu, ekonomski ima smisla migrirati.

## Cost guard / alerts

**Trenutno:** nema. Svaki API poziv prolazi bez cap-a.

**Predlog (post-launch P1):**
- Cron koji svaki sat čita `Stats` i upoređuje sa budgetom
- Webhook alert kad mjesečna potrošnja pređe 80% ($X)
- Refuse new requests preko 100% (configurable)
- Per-IP rate limit na `/api/chat` da spriječi abuse

Implementacija ide u Sesiju 11+ (post-launch hardening).

## Anthropic kredit

Trenutno: ručno dopunjavanje preko [console.anthropic.com](https://console.anthropic.com) → Plans & Billing.

**Preporučeno:** uključiti **auto-recharge** (npr. dopuni $10 kad padne ispod $2). Bez toga, kredit se može potrošiti u trenu velikog traffic-a i chat počne vraćati graceful fallback poruku ("Tehnički zastoj, kontakt 066...").

## Azure Speech free tier

500.000 znakova/mjesec TTS + 5h STT besplatno. Naš TTS prosječno ~200 znakova per voice odgovor → 2.500 voice odgovora/mj u free tier-u. Iznad → $4 / 1M znakova ($1 / ~250.000 znakova).

## Groq Whisper free tier

7.200 sekundi/dan = 2 sata audio transkripcije. Za naš volumen ne bi trebao biti problem. Iznad → $0.04 / minut audio.

## Optimizacijske mete (Sesija 9 fokus)

1. **Manje input tokena** — system prompt je sad ~3.500 tokena (kategorije + pravila). Možda možemo komprimovati.
2. **Cache prompt** (Anthropic prompt caching) — sistem prompt se ne mijenja, kandidat za cache. Smanjuje input cost na 10% za cache hit.
3. **Manji model za prvi pass** — Haiku za klasifikaciju, Sonnet samo ako Haiku eskalira.
4. **GPT-4o-mini eval** — $0.15 / $0.60 per 1M, 20× jeftiniji od Sonneta.
