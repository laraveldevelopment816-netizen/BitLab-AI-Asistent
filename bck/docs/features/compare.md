# Compare endpoint

> Fan-out istog upita kroz N modela paralelno, side-by-side rezultati sa metrikama (latency, tokens, cost).

## Zašto

Bez compare panela ne znamo:
- Da li jeftiniji model (Haiku, GPT-4o-mini) može uraditi isto što Sonnet
- Koji model rješava specifičan use case bolje (kategorijska klasifikacija, custom build poziv, voice format)
- Koliko je razlika u cost vs quality vrijedna

Compare panel daje konkretne brojke za svaki upit.

## Kako se koristi

### 1. Kroz dashboard

Otvori `/admin/compare`:
1. Paste prompt
2. Izaberi channel (chat / voice / email)
3. Izaberi modele za poređenje (default: haiku + sonnet)
4. Klik **Run on N models**
5. Vidi side-by-side card-ove sa replyem, latency, tokens, cost, tool call summary
6. Klik na request_id linkove za pun RequestDetail timeline

### 2. Direktno API call

```bash
curl -sX POST https://<domain>/api/dashboard/compare \
  -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "imate li tastaturu",
    "channel": "chat",
    "models": ["haiku", "sonnet"]
  }'
```

Vraća:
```json
{
  "compare_group_id": "21d33932993b4b54a318a13699c7a4b8",
  "results": [
    {
      "model_key": "haiku",
      "model": "claude-haiku-4-5-20251001",
      "request_id": 14,
      "status": "ok",
      "reply": "Imamo nekoliko tastatura...",
      "tokens_in": 9467,
      "tokens_out": 215,
      "latency_ms": 6470,
      "cost_usd": 0.0105,
      "tool_calls": [
        {"iteration":1, "tool_name":"search_products",
         "input_json":"{\"query\":\"tastatura\",\"category_id\":\"220\"}",
         "output_text":"...", "latency_ms":3500}
      ]
    },
    {
      "model_key": "sonnet",
      "model": "claude-sonnet-4-6",
      "request_id": 15,
      "status": "ok",
      "reply": "Evo tastatura iz našeg kataloga...",
      "tokens_in": 13834,
      "tokens_out": 257,
      "latency_ms": 17074,
      "cost_usd": 0.0454,
      "tool_calls": [...]
    }
  ]
}
```

## Implementacija

`app/server/dashboard.py` `compare_models()`:

```python
async def compare_models(req: CompareRequest):
    group_id = uuid.uuid4().hex
    base_messages = list(req.history or [])
    base_messages.append({"role": "user", "content": req.message})

    async def _run_one(model_key: str) -> CompareResultItem:
        full_model = registry[model_key]
        try:
            result = await asyncio.to_thread(
                run_agent, base_messages, req.channel, full_model
            )
            request_id = await _persist_trace(
                channel=req.channel, model=full_model, prompt=req.message,
                result=result, compare_group_id=group_id,
            )
            ...

    results = await asyncio.gather(*[_run_one(m) for m in req.models])
    return CompareResponse(compare_group_id=group_id, results=list(results))
```

**Ključ:** `asyncio.gather` šalje sve modele paralelno — ukupno trajanje = max(svih) + epsilon, ne sum.

## Model registry

`app/config.py`:
```python
@property
def model_registry(self) -> dict[str, str]:
    return {
        "haiku": self.chat_model,    # default chat_model env var
        "sonnet": self.email_model,  # default email_model env var
    }
```

Trenutno samo Anthropic. Sesija 9 (model eval) dodaje GPT-4o-mini, Llama 3.x, DeepSeek-V3 — vidi [`../plans/model-eval.md`](../plans/model-eval.md).

## Logging

Sva paralelna izvršavanja se loguju u `requests` tabelu sa istim `compare_group_id`. Filter u Live/History po tom group ID-u → vidiš grupisano.

## Cost izračun

`COST_PER_M` u `dashboard.py`:
```python
COST_PER_M = {
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00},
}
```

Po request:
```python
cost = (tokens_in × in_rate + tokens_out × out_rate) / 1_000_000
```

Primjer iz tabele iznad:
- Haiku: (9467 × 1 + 215 × 5) / 1M = $0.0105
- Sonnet: (13834 × 3 + 257 × 15) / 1M = $0.0454

Sonnet je ~4.3× skuplji na ovom upitu, sporiji 2.6×, ali (može da) daje bolje formatirane rezultate.

## Granica

Trenutno nema timeout-a po model-u — ako Sonnet zaglavi, Compare vraća tek poslije njegovog timeout-a. n8n / dashboard bi trebao imati 30s deadline na svoju stranu.

`max_length: 4` u request validatoru — ne dozvoljava više od 4 modela paralelno (sprečava cost spike i rate limit).

## Implementacija

| Element | Lokacija |
|---|---|
| API endpoint | `app/server/dashboard.py` `compare_models()` |
| Pydantic schemas | `CompareRequest`, `CompareResultItem`, `CompareResponse` |
| Frontend Compare page | `dashboard/src/pages/Compare.tsx` |
| API client | `dashboard/src/api.ts` `api.compare()` |
| Cost rate table | `dashboard/src/api.ts` (frontend) + `app/server/dashboard.py` `COST_PER_M` (backend) |
