# Live beta monitoring

Operativna referenca za admine dok je BitLab AI Asistent u **live beta**
modu (beta badge na widget-u). Cilj: rana detekcija problema u produkciji.

Sve do uklanjanja beta badge-a iz widget-a, ovaj fajl je aktivan i prati
se. Backend restart skripte: [`../../README.md`](../../README.md#backend-restart).

Istorijski log prvog LIVE puštanja (2026-05-08): [`../archives/live-2026-05-08.md`](../archives/live-2026-05-08.md).

---

## Dashboard tabovi — šta gledamo

Otvori dashboard u tabu na telefonu/laptopu:
**`https://aiasistent.bitlab.rs/admin/`** (Bearer ključ je u `shared/.env`
servera, podsjetnik: env var `DASHBOARD_API_KEY`).

| Tab | Šta gledamo | Akcija ako vidiš |
|---|---|---|
| **Sessions** | Broj ulazaka, broj poruka po sesiji, koliko ide do `escalate_to_human` | >5 escalate u 30 min = problem, otvori History |
| **History** | Filter na `channel=chat` — pročitaj 5–10 random sesija svaka 30 min | Halucinacija o cijenama / nepostojećim proizvodima → zovi Branislava |
| **Tool calls** | `search_products` poziv treba imati `category_id` i (često) `brand_id` popunjen | Ako su prazni za očigledne upite ("samsung tv") → AI ne klasifikuje, javi nam |
| **Errors** | Crveni badge na vrhu | Otvori Sessions → klikni sesiju → vidi trace |

Na telefonu dashboard je responsive. Brzi pristup: bookmark
`https://aiasistent.bitlab.rs/admin/sessions`.

---

## Eskalacijski put

| Šta | Akcija |
|---|---|
| Backend down (502/503) | SSH → `systemctl restart aiasistent-prod` (vidi [`../../README.md`](../../README.md#backend-restart)) |
| TTS šalje 503 | Provjeri da fallback chain radi (Azure ili edge-tts) |
| STT halucinira ("hvala", "...") | Već imamo guard `_HALLUCINATIONS` u `/api/stt` |
| Halucinacije proizvoda u chat-u | Pošalji sifru/sesija ID na Viber, gledamo da li je nova pretraga riješila |
| Korisnik traži B2B / JIB | Trigger-uje `escalate_to_human` automatski — Brana dobija email |

Hitno → Viber.
